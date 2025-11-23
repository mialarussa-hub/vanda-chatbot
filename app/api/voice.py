"""
Voice API Endpoint per VANDA Chatbot.

Gestisce conversione Text-to-Speech con ElevenLabs API.
Supporta chunked TTS per playback real-time durante lo streaming LLM.

Endpoint: POST /api/voice/tts-chunk
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Generator
from loguru import logger
import requests
import time
from app.config import settings

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TTSRequest(BaseModel):
    """
    Request body per POST /api/voice/tts-chunk.
    """
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text to convert to speech (max 5000 chars)"
    )
    voice_id: Optional[str] = Field(
        default=None,
        description="ElevenLabs voice ID (uses default if not specified)"
    )
    stability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Voice stability (0.0-1.0). Higher = more consistent, less expressive"
    )
    similarity_boost: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Similarity to original voice (0.0-1.0)"
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="Speech speed (0.25-4.0)"
    )


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(tags=["voice"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def call_elevenlabs_tts_stream(
    text: str,
    voice_id: str,
    model_id: str,
    voice_settings: dict,
    max_retries: int = 3
) -> Generator[bytes, None, None]:
    """
    Chiama ElevenLabs TTS API in modalità streaming.

    Yields:
        bytes: Audio MP3 chunks
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    params = {
        "optimize_streaming_latency": 3,
        "output_format": "mp3_44100_128"
    }

    payload = {
        "text": text,
        "model_id": model_id,
        "language_code": "it",
        "voice_settings": voice_settings
    }

    for attempt in range(max_retries):
        try:
            logger.info(f"ElevenLabs TTS streaming request (attempt {attempt + 1}/{max_retries})")

            with requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                stream=True,
                timeout=30
            ) as response:
                if response.status_code == 200:
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk:
                            yield chunk
                    return

                # Handle errors (same logic as before)
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
                else:
                    logger.error(f"ElevenLabs error: {response.status_code} - {response.text}")
                    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "TTS generation failed")

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            if attempt == max_retries - 1:
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post(
    "/voice/tts-chunk",
    response_class=StreamingResponse,
    summary="Text-to-Speech Chunk Conversion (Streaming)",
    description="Streams MP3 audio from ElevenLabs"
)
async def tts_chunk(request: TTSRequest):
    """
    Converte testo in audio MP3 (Streaming).
    """
    try:
        if not request.text or len(request.text.strip()) == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Text cannot be empty")

        selected_voice_id = request.voice_id or settings.ELEVENLABS_VOICE_ID

        voice_settings = {
            "stability": request.stability,
            "similarity_boost": request.similarity_boost,
            "use_speaker_boost": True,
            "speed": request.speed
        }

        return StreamingResponse(
            call_elevenlabs_tts_stream(
                text=request.text,
                voice_id=selected_voice_id,
                model_id=settings.ELEVENLABS_MODEL_ID,
                voice_settings=voice_settings
            ),
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"TTS endpoint error: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get(
    "/voice/health",
    summary="Voice service health check",
    description="Verifica che il servizio TTS ElevenLabs sia configurato correttamente"
)
async def voice_health():
    """
    Health check per il servizio voice/TTS.

    Verifica che l'API key ElevenLabs sia configurata.
    """
    try:
        has_api_key = bool(settings.ELEVENLABS_API_KEY)

        return {
            "status": "healthy" if has_api_key else "unconfigured",
            "provider": "ElevenLabs",
            "tts_configured": has_api_key,
            "default_voice_id": settings.ELEVENLABS_VOICE_ID,
            "default_model": settings.ELEVENLABS_MODEL_ID
        }
    except Exception as e:
        logger.error(f"Voice health check error: {e}")
        return {
            "status": "unhealthy",
            "provider": "ElevenLabs",
            "error": str(e)
        }
