"""
Voice API Endpoint per VANDA Chatbot.

Gestisce conversione Text-to-Speech con OpenAI TTS API.
Supporta chunked TTS per playback real-time durante lo streaming LLM.

Endpoint: POST /api/voice/tts-chunk
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Literal
from loguru import logger
import openai
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
        max_length=4096,
        description="Text to convert to speech (max 4096 chars per API limits)"
    )
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        default="nova",
        description="OpenAI TTS voice to use"
    )
    model: Literal["tts-1", "tts-1-hd"] = Field(
        default="tts-1",
        description="TTS model (tts-1 = standard, tts-1-hd = high quality)"
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="Speech speed (0.25 - 4.0)"
    )


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(tags=["voice"])


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
        500: {"description": "Internal server error"}
    },
    summary="Text-to-Speech Chunk Conversion",
    description="Converts text chunk to MP3 audio using OpenAI TTS API"
)
async def tts_chunk(request: TTSRequest):
    """
    Converte un chunk di testo in audio MP3.

    Usato per playback real-time durante streaming LLM:
    1. Frontend accumula parole fino a frase completa (~20 parole o . ! ?)
    2. Invia chunk a questo endpoint
    3. Riceve MP3 audio
    4. Aggiunge a queue di playback
    5. Seamless playback mentre LLM continua streaming

    **Args:**
    - text: Testo da convertire (max 4096 chars per OpenAI limits)
    - voice: Voce da usare (nova = femminile energica consigliata)
    - model: tts-1 (standard) o tts-1-hd (alta qualità)
    - speed: Velocità parlato (default 1.0)

    **Returns:**
    - audio/mpeg: Binary MP3 audio stream

    **Example:**
    ```json
    {
        "text": "Il progetto Campana di Ferro rappresenta uno dei nostri lavori più significativi.",
        "voice": "nova",
        "model": "tts-1",
        "speed": 1.0
    }
    ```
    """
    try:
        logger.info(f"TTS request - {len(request.text)} chars, voice: {request.voice}")

        # ====================================================================
        # OPENAI TTS API CALL
        # ====================================================================

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        # Call TTS API
        response = client.audio.speech.create(
            model=request.model,
            voice=request.voice,
            input=request.text,
            speed=request.speed,
            response_format="mp3"
        )

        # Get audio binary data
        audio_data = response.content

        logger.info(f"TTS generated - {len(audio_data)} bytes MP3")

        # ====================================================================
        # RETURN MP3 AUDIO
        # ====================================================================

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=\"speech.mp3\"",
                "Cache-Control": "no-cache"
            }
        )

    except openai.OpenAIError as e:
        logger.error(f"OpenAI TTS error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS generation failed: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error in TTS: {e}", exc_info=True)
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
    description="Verifica che il servizio TTS sia configurato correttamente"
)
async def voice_health():
    """
    Health check per il servizio voice/TTS.

    Verifica che l'API key OpenAI sia configurata.
    """
    try:
        has_api_key = bool(settings.OPENAI_API_KEY)

        return {
            "status": "healthy" if has_api_key else "unconfigured",
            "tts_configured": has_api_key,
            "default_voice": settings.OPENAI_TTS_VOICE,
            "default_model": settings.OPENAI_TTS_MODEL
        }
    except Exception as e:
        logger.error(f"Voice health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
