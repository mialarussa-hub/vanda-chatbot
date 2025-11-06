"""
Chat API Endpoint per VANDA Chatbot.

Endpoint principale che integra:
- RAG Service (recupero documenti)
- LLM Service (generazione risposte)
- Memory Manager (persistenza conversazioni)
- Streaming SSE support

Endpoint: POST /api/chat
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Generator
from datetime import datetime
from loguru import logger
import json
import uuid
import asyncio

from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
from app.services.memory_manager import memory_manager
from app.services.embedding_service import embedding_service
from app.models.schemas import MessageRole, MetadataFilter


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """
    Request body per POST /api/chat.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Messaggio utente"
    )
    session_id: Optional[str] = Field(
        None,
        description="UUID sessione (generato automaticamente se omesso)"
    )
    stream: bool = Field(
        default=True,
        description="Se True, ritorna SSE stream. Se False, ritorna JSON completo"
    )
    use_rag: bool = Field(
        default=True,
        description="Se True, usa RAG per recuperare documenti rilevanti"
    )
    rag_filters: Optional[MetadataFilter] = Field(
        default=None,
        description="Filtri opzionali per RAG (category, project_type, etc.)"
    )
    include_sources: bool = Field(
        default=False,
        description="Se True, include documenti sorgente nella risposta"
    )

    @validator('session_id')
    def validate_session_id(cls, v):
        """Valida formato UUID del session_id."""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError("session_id deve essere un UUID valido")
        return v


class ChatResponse(BaseModel):
    """
    Response body per modalità non-streaming.
    """
    session_id: str = Field(..., description="UUID sessione")
    message: str = Field(..., description="Risposta assistant")
    sources: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Documenti sorgente utilizzati (se include_sources=True)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata aggiuntivi (tokens_used, processing_time, etc.)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp risposta"
    )


class ErrorResponse(BaseModel):
    """Response body per errori."""
    error: str = Field(..., description="Messaggio errore")
    detail: Optional[str] = Field(None, description="Dettagli aggiuntivi")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(tags=["chat"])


# ============================================================================
# CHAT ENDPOINT
# ============================================================================

@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        200: {"description": "Risposta generata con successo"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Chat con VANDA Assistant",
    description="Invia un messaggio al chatbot e ricevi una risposta (streaming o completa)"
)
async def chat(request: ChatRequest):
    """
    Endpoint principale del chatbot.

    **Flusso:**
    1. Valida richiesta e genera session_id se necessario
    2. Recupera history conversazione da Memory Manager
    3. Se use_rag=True: genera embedding e cerca documenti rilevanti
    4. Genera risposta con LLM (streaming o completa)
    5. Salva messaggi in Memory Manager
    6. Ritorna risposta (SSE stream o JSON)

    **Esempi:**

    Non-streaming (JSON completo):
    ```json
    {
        "message": "Parlami dei vostri progetti",
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "stream": false
    }
    ```

    Streaming (SSE):
    ```json
    {
        "message": "Parlami dei vostri progetti",
        "stream": true
    }
    ```
    """
    try:
        # ====================================================================
        # 1. SETUP SESSIONE
        # ====================================================================

        # Genera session_id se non fornito
        if not request.session_id:
            request.session_id = memory_manager.generate_session_id()
            logger.info(f"Generated new session_id: {request.session_id}")

        logger.info(
            f"Chat request - session: {request.session_id}, "
            f"stream: {request.stream}, use_rag: {request.use_rag}"
        )

        # ====================================================================
        # 2. RECUPERA HISTORY CONVERSAZIONE
        # ====================================================================

        conversation_history = memory_manager.get_history(
            session_id=request.session_id,
            limit=10,  # Ultimi 10 messaggi (ridotto per performance)
            include_system=False
        )

        logger.info(
            f"📜 HISTORY: Retrieved {len(conversation_history)} messages for session {request.session_id[:8]}..."
        )

        # Log dettagliato della history (primi 50 char di ogni messaggio)
        if conversation_history:
            for i, msg in enumerate(conversation_history):
                preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                logger.info(f"  [{i+1}] {msg.role}: {preview}")

        # ====================================================================
        # 3. RAG - RECUPERO DOCUMENTI RILEVANTI
        # ====================================================================

        rag_context = None
        retrieved_documents = []

        if request.use_rag:
            try:
                # Genera embedding della query
                logger.debug("Generating embedding for query...")
                query_embedding = embedding_service.get_embedding(
                    text=request.message
                )

                # Cerca documenti simili
                logger.debug("Searching similar documents...")
                documents = rag_service.search_similar_documents(
                    query_embedding=query_embedding,
                    match_count=5,  # Top 5 documenti per avere più contesto
                    match_threshold=0.60,  # Soglia bilanciata per qualità e quantità
                    metadata_filter=request.rag_filters
                )

                if documents:
                    logger.info(f"Found {len(documents)} relevant documents")

                    # Formatta context per LLM
                    rag_context = rag_service.format_context_for_llm(
                        documents=documents,
                        include_metadata=True
                    )

                    # Salva documenti per risposta (se richiesto)
                    if request.include_sources:
                        retrieved_documents = [
                            {
                                "id": doc["id"],
                                "content": doc["content"][:200] + "...",
                                "similarity": round(doc["similarity"], 3),
                                "metadata": doc.get("metadata", {})
                            }
                            for doc in documents
                        ]
                else:
                    logger.warning("No relevant documents found")

            except Exception as e:
                logger.error(f"RAG error: {e}")
                # Continua senza RAG in caso di errore
                rag_context = None

        # ====================================================================
        # 4. SALVA USER MESSAGE
        # ====================================================================

        user_message_id = memory_manager.add_message(
            session_id=request.session_id,
            role=MessageRole.USER,
            content=request.message,
            metadata={}
        )

        if not user_message_id:
            logger.warning("Failed to save user message to database")

        # ====================================================================
        # 5. GENERA RISPOSTA (STREAMING O COMPLETA)
        # ====================================================================

        if request.stream:
            # ----------------------------------------------------------------
            # MODALITÀ STREAMING (SSE)
            # ----------------------------------------------------------------

            logger.info("Generating streaming response...")

            async def generate_stream():
                """
                Generator per SSE streaming.

                Formato SSE:
                - Token: "data: {content}\\n\\n"
                - Sorgenti: "data: [SOURCES]{json}\\n\\n"
                - Fine: "data: [DONE]\\n\\n"
                - Errore: "data: [ERROR]{message}\\n\\n"
                """
                try:
                    full_response = ""

                    # Stream tokens dal LLM (generator sincrono)
                    for chunk in llm_service.generate_streaming_response(
                        user_message=request.message,
                        conversation_history=conversation_history,
                        rag_context=rag_context
                    ):
                        # chunk è già in formato SSE: "data: {content}\n\n"
                        yield chunk

                        # FORZA FLUSH IMMEDIATO: piccolo delay per forzare invio al client
                        await asyncio.sleep(0)  # Yield control, forza invio buffer

                        # Accumula risposta completa per salvare su DB
                        # IMPORTANTE: Preserviamo tutti gli spazi nel contenuto!
                        if chunk.startswith("data: "):
                            # Rimuove "data: " all'inizio e newlines alla fine preservando spazi
                            content = chunk[6:].rstrip('\n')
                            if content not in ["[DONE]", "[ERROR]"] and not content.startswith("[ERROR]"):
                                full_response += content

                    # Invia sorgenti se richieste
                    if request.include_sources and retrieved_documents:
                        sources_json = json.dumps(retrieved_documents)
                        yield f"data: [SOURCES]{sources_json}\n\n"

                    # Salva assistant response su DB
                    memory_manager.add_message(
                        session_id=request.session_id,
                        role=MessageRole.ASSISTANT,
                        content=full_response,
                        metadata={
                            "model": llm_service.model,
                            "rag_enabled": request.use_rag,
                            "documents_used": len(retrieved_documents) if retrieved_documents else 0
                        }
                    )

                    logger.info(f"Streaming completed - {len(full_response)} chars")

                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: [ERROR]Si è verificato un errore: {str(e)}\n\n"

            # Ritorna StreamingResponse
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disabilita buffering nginx
                    "Transfer-Encoding": "chunked",
                }
            )

        else:
            # ----------------------------------------------------------------
            # MODALITÀ NON-STREAMING (JSON completo)
            # ----------------------------------------------------------------

            logger.info("Generating complete response...")

            result = llm_service.generate_response(
                user_message=request.message,
                conversation_history=conversation_history,
                rag_context=rag_context
            )

            # Salva assistant response su DB
            memory_manager.add_message(
                session_id=request.session_id,
                role=MessageRole.ASSISTANT,
                content=result["response"],
                metadata={
                    "model": llm_service.model,
                    "tokens_used": result.get("tokens_used", 0),
                    "rag_enabled": request.use_rag,
                    "documents_used": len(retrieved_documents) if retrieved_documents else 0
                }
            )

            # Costruisci risposta
            response = ChatResponse(
                session_id=request.session_id,
                message=result["response"],
                sources=retrieved_documents if request.include_sources else None,
                metadata={
                    "tokens_used": result.get("tokens_used", 0),
                    "processing_time_ms": result.get("processing_time_ms", 0),
                    "model": llm_service.model,
                    "rag_enabled": request.use_rag,
                    "documents_found": len(retrieved_documents)
                }
            )

            logger.info(
                f"Response generated - {len(result['response'])} chars, "
                f"{result.get('tokens_used', 0)} tokens"
            )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.model_dump(mode='json')
            )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error="Invalid request",
                detail=str(e)
            ).model_dump(mode='json')
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal server error",
                detail="Si è verificato un errore durante l'elaborazione della richiesta"
            ).model_dump(mode='json')
        )


# ============================================================================
# HEALTH CHECK / INFO ENDPOINTS
# ============================================================================

@router.get(
    "/chat/health",
    summary="Health check del chat service",
    description="Verifica che tutti i servizi siano inizializzati"
)
async def chat_health():
    """
    Health check per il chat service.

    Verifica che tutti i servizi siano inizializzati correttamente.
    """
    try:
        services_status = {
            "rag_service": rag_service is not None,
            "llm_service": llm_service is not None,
            "memory_manager": memory_manager is not None,
            "embedding_service": embedding_service is not None
        }

        all_healthy = all(services_status.values())

        return JSONResponse(
            status_code=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "healthy" if all_healthy else "unhealthy",
                "services": services_status,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get(
    "/chat/stats",
    summary="Statistiche sessioni",
    description="Recupera statistiche generali sulle sessioni attive"
)
async def chat_stats():
    """
    Recupera statistiche sulle sessioni.

    Ritorna numero di sessioni attive e statistiche aggregate.
    """
    try:
        sessions = memory_manager.get_sessions(active_only=True)

        total_messages = sum(s["message_count"] for s in sessions)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "active_sessions": len(sessions),
                "total_messages": total_messages,
                "avg_messages_per_session": round(total_messages / len(sessions), 2) if sessions else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post(
    "/chat/reload-config",
    summary="Reload configurazioni",
    description="Ricarica le configurazioni dinamiche dal database"
)
async def reload_config():
    """
    Ricarica le configurazioni dinamiche dal database.

    Questo endpoint:
    1. Svuota la cache del ConfigService
    2. Ricarica le configurazioni di LLMService
    3. Ricarica le configurazioni di RAGService

    Returns:
        JSONResponse con status del reload
    """
    try:
        logger.info("Reload config requested")

        results = {
            "llm_service": False,
            "rag_service": False
        }

        # Reload LLM Service
        if llm_service:
            results["llm_service"] = llm_service.reload_config()

        # Reload RAG Service
        if rag_service:
            results["rag_service"] = rag_service.reload_config()

        success = all(results.values())

        return JSONResponse(
            status_code=status.HTTP_200_OK if success else status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "success" if success else "partial_failure",
                "services_reloaded": results,
                "message": "Configurations reloaded successfully" if success else "Some services failed to reload",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Reload config error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
