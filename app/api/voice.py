"""
Voice API Endpoint per VANDA Chatbot.

Gestisce conversione Text-to-Speech con ElevenLabs API.
Supporta chunked TTS per playback real-time durante lo streaming LLM.

Endpoint: POST /api/voice/tts-chunk
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional
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

def call_elevenlabs_tts(
    text: str,
    voice_id: str,
    model_id: str,
    voice_settings: dict,
    max_retries: int = 3
) -> bytes:
    """
    Chiama ElevenLabs TTS API con retry logic.

    Args:
        text: Testo da convertire in audio
        voice_id: ID della voce ElevenLabs
        model_id: ID del modello (es. eleven_turbo_v2_5)
        voice_settings: Dizionario con stability, similarity_boost, etc.
        max_retries: Numero massimo di retry in caso di errore

    Returns:
        bytes: Audio MP3 data

    Raises:
        HTTPException: In caso di errore API o timeout
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
        "language_code": "it",  # Forza italiano
        "voice_settings": voice_settings
    }

    for attempt in range(max_retries):
        try:
            logger.info(f"ElevenLabs TTS request (attempt {attempt + 1}/{max_retries}) - {len(text)} chars")

            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                stream=True,
                timeout=30
            )

            # Success
            if response.status_code == 200:
                audio_data = b""
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        audio_data += chunk

                logger.info(f"ElevenLabs TTS success - {len(audio_data)} bytes MP3")
                return audio_data

            # Rate limit - retry con exponential backoff
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)
                    logger.warning(f"Rate limit hit. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("Rate limit exceeded after retries")
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="ElevenLabs rate limit exceeded. Please try again later."
                    )

            # Validation error - non ritentare
            elif response.status_code == 422:
                error_detail = response.json() if response.content else response.text
                logger.error(f"ElevenLabs validation error: {error_detail}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request parameters: {error_detail}"
                )

            # Unauthorized - non ritentare
            elif response.status_code == 401:
                logger.error("ElevenLabs authentication failed")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="TTS service authentication failed"
                )

            # Server error - retry
            elif response.status_code >= 500:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    logger.warning(f"ElevenLabs server error. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"ElevenLabs server error after retries: {response.status_code}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="TTS service temporarily unavailable"
                    )

            # Altri errori
            else:
                logger.error(f"ElevenLabs unexpected error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"TTS generation failed: {response.status_code}"
                )

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                logger.warning(f"Request timeout. Retrying...")
                time.sleep(2 ** attempt)
                continue
            else:
                logger.error("Request timeout after retries")
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="TTS service timeout"
                )

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"Network error: {e}. Retrying...")
                time.sleep(2 ** attempt)
                continue
            else:
                logger.error(f"Network error after retries: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Network error connecting to TTS service"
                )

    # Fallback (non dovrebbe mai arrivare qui)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to generate audio after retries"
    )


# ============================================================================
# TTS ENDPOINT
# ============================================================================

@router.post(
    "/voice/tts-chunk",
    response_class=Response,
    responses={
        200: {
            "content": {"audio/mpeg": {}},
            "description": "MP3 audio chunk"
        },
        400: {"description": "Bad request"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"}
    },
    summary="Text-to-Speech Chunk Conversion",
    description="Converts text chunk to MP3 audio using ElevenLabs TTS API"
)
async def tts_chunk(request: TTSRequest):
    """
    Converte un chunk di testo in audio MP3 usando ElevenLabs.

    Usato per playback real-time durante streaming LLM:
    1. Frontend accumula parole fino a frase completa (~20 parole o . ! ?)
    2. Invia chunk a questo endpoint
    3. Riceve MP3 audio
    4. Aggiunge a queue di playback
    5. Seamless playback mentre LLM continua streaming

    **Args:**
    - text: Testo da convertire (max 5000 chars)
    - voice_id: ID voce ElevenLabs (opzionale, usa default se non specificato)
    - stability: Stabilità voce 0.0-1.0 (default: 0.5)
    - similarity_boost: Similarità alla voce originale 0.0-1.0 (default: 0.8)
    - speed: Velocità parlato 0.25-4.0 (default: 1.0)

    **Returns:**
    - audio/mpeg: Binary MP3 audio stream

    **Example:**
    ```json
    {
        "text": "Il progetto Campana di Ferro rappresenta uno dei nostri lavori più significativi.",
        "voice_id": "QITiGyM4owEZrBEf0QV8",
        "stability": 0.5,
        "similarity_boost": 0.8,
        "speed": 1.0
    }
    ```
    """
    try:
        # Validazione base
        if not request.text or len(request.text.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text cannot be empty"
            )

        # Usa voice_id fornito o default da config
        selected_voice_id = request.voice_id or settings.ELEVENLABS_VOICE_ID

        # Prepara voice settings
        voice_settings = {
            "stability": request.stability,
            "similarity_boost": request.similarity_boost,
            "use_speaker_boost": True,
            "speed": request.speed
        }

        # Chiama ElevenLabs API
        audio_data = call_elevenlabs_tts(
            text=request.text,
            voice_id=selected_voice_id,
            model_id=settings.ELEVENLABS_MODEL_ID,
            voice_settings=voice_settings
        )

        # Restituisci MP3 audio
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=\"speech.mp3\"",
                "Cache-Control": "no-cache"
            }
        )

    except HTTPException:
        # Re-raise HTTPException (già gestite)
        raise

    except Exception as e:
        logger.error(f"Unexpected error in TTS endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate audio"
        )


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
