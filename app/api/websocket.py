"""
WebSocket API Endpoint per VANDA Chatbot.

Gestisce la comunicazione real-time full-duplex per:
- Ricezione messaggi utente (testo/audio)
- Streaming risposta LLM (testo)
- Streaming risposta TTS (audio)
- Controllo stato (Start/Stop speaking) per echo cancellation
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.llm_service import llm_service
from app.services.memory_manager import memory_manager
from app.services.rag_service import rag_service
from app.services.embedding_service import embedding_service
from app.services.intent_classifier import intent_classifier
from app.models.schemas import MessageRole, MetadataFilter
from app.config import settings
from loguru import logger
import json
import asyncio
import aiohttp
from typing import Optional

router = APIRouter(tags=["websocket"])

# Configurazione ElevenLabs
ELEVENLABS_API_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.ELEVENLABS_VOICE_ID}/stream"
ELEVENLABS_HEADERS = {
    "xi-api-key": settings.ELEVENLABS_API_KEY,
    "Content-Type": "application/json"
}

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    session_id = None

    try:
        while True:
            # 1. Ricevi messaggio dal client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_message = message_data.get("message")
            session_id = message_data.get("session_id")
            
            if not session_id:
                session_id = memory_manager.generate_session_id()
                await websocket.send_json({"type": "session_init", "session_id": session_id})

            if not user_message:
                continue

            logger.info(f"WS Message received: {user_message[:50]}...")

            # 2. Invia segnale [START_SPEAKING] per disattivare microfono client (Echo Cancellation)
            await websocket.send_json({"type": "control", "signal": "start_speaking"})

            # 3. Pipeline RAG (opzionale ma raccomandata)
            rag_context = None
            try:
                # Detect intent/category
                detected_category = intent_classifier.detect_category(user_message)
                rag_filters = MetadataFilter(category=detected_category) if detected_category else None
                
                # Embedding & Search
                query_embedding = embedding_service.get_embedding(user_message)
                documents = rag_service.search_similar_documents(
                    query_embedding=query_embedding,
                    query_text=user_message,
                    metadata_filter=rag_filters
                )
                
                if documents:
                    rag_context = rag_service.format_context_for_llm(documents)
                    # Invia sources al client
                    sources = [{"id": d["id"], "content": d["content"][:100]} for d in documents]
                    await websocket.send_json({"type": "sources", "data": sources})
            except Exception as e:
                logger.error(f"RAG Error in WS: {e}")

            # 4. Salva messaggio utente
            memory_manager.add_message(session_id, MessageRole.USER, user_message)

            # 5. Generazione LLM + TTS Streaming
            # Usiamo una queue per bufferizzare il testo e inviarlo a ElevenLabs
            # mentre inviamo parallelamente il testo al client
            
            full_response_text = ""
            current_sentence = ""
            
            # Recupera history
            history = memory_manager.get_history(session_id, limit=10)

            async for chunk in llm_service.generate_streaming_response_content(
                user_message=user_message,
                conversation_history=history,
                rag_context=rag_context
            ):
                # chunk è il testo puro (non SSE format)
                if not chunk:
                    continue
                    
                full_response_text += chunk
                current_sentence += chunk
                
                # Invia testo parziale al client per UI
                await websocket.send_json({"type": "text_chunk", "content": chunk})

                # Logica semplice per chunking TTS: spezza su punteggiatura forte
                if any(punct in chunk for punct in [".", "!", "?", ";"]):
                    # Invia sentence a ElevenLabs
                    if len(current_sentence.strip()) > 5: # Minimo caratteri per evitare glitch
                        await stream_audio_chunk(websocket, current_sentence)
                        current_sentence = ""

            # Invia eventuale testo residuo
            if current_sentence.strip():
                await stream_audio_chunk(websocket, current_sentence)

            # 6. Salva risposta assistant
            memory_manager.add_message(session_id, MessageRole.ASSISTANT, full_response_text)

            # 7. Invia segnale [STOP_SPEAKING] per riattivare microfono
            await websocket.send_json({"type": "control", "signal": "stop_speaking"})
            
            # Segnale fine turno
            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

async def stream_audio_chunk(websocket: WebSocket, text: str):
    """
    Chiama ElevenLabs e invia audio bytes via WebSocket
    """
    try:
        # Pulisci testo (minimo indispensabile)
        clean_text = text.replace("*", "").strip()
        if not clean_text:
            return

        logger.debug(f"TTS Streaming chunk: {clean_text[:30]}...")

        async with aiohttp.ClientSession() as session:
            payload = {
                "text": clean_text,
                "model_id": settings.ELEVENLABS_MODEL_ID,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                "optimize_streaming_latency": 3,
                "output_format": "mp3_44100_128"
            }
            
            async with session.post(ELEVENLABS_API_URL, json=payload, headers=ELEVENLABS_HEADERS) as response:
                if response.status != 200:
                    logger.error(f"ElevenLabs API Error: {response.status}")
                    return
                
                # Leggi stream e invia bytes
                async for chunk in response.content.iter_chunked(1024):
                    if chunk:
                        # Invia binary frame
                        await websocket.send_bytes(chunk)
                        
    except Exception as e:
        logger.error(f"TTS Stream Error: {e}")
