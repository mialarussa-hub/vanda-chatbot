"""
VANDA Chatbot - FastAPI Application Entry Point

Entry point principale per Google Cloud Run.
Inizializza FastAPI app con tutti i servizi e router.

Run locale:
    uvicorn main:app --reload --port 8080

Deploy Cloud Run:
    gcloud run deploy vanda-chatbot --source .
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.config import settings
from app.api.chat import router as chat_router
from app.api.voice import router as voice_router


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Configura loguru per Cloud Run (JSON format)
logger.remove()  # Rimuovi handler default

# Console logging (colorato per dev, JSON per prod)
if settings.ENV == "production":
    # Formato JSON per Cloud Run logs
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        level=settings.LOG_LEVEL,
        serialize=False  # Cloud Run gestisce il JSON
    )
else:
    # Formato leggibile per sviluppo
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL
    )


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestisce startup e shutdown dell'applicazione.

    Startup: Verifica che tutti i servizi siano inizializzati
    Shutdown: Cleanup risorse se necessario
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info("=" * 80)
    logger.info("VANDA CHATBOT - Starting up...")
    logger.info("=" * 80)

    try:
        # Import dei servizi (inizializzazione singleton)
        from app.services.rag_service import rag_service
        from app.services.llm_service import llm_service
        from app.services.memory_manager import memory_manager
        from app.services.embedding_service import embedding_service

        # Verifica servizi
        services_ok = all([
            rag_service is not None,
            llm_service is not None,
            memory_manager is not None,
            embedding_service is not None
        ])

        if not services_ok:
            logger.error("❌ Some services failed to initialize!")
            raise RuntimeError("Service initialization failed")

        logger.info("✅ All services initialized successfully")
        logger.info(f"   - Environment: {settings.ENV}")
        logger.info(f"   - LLM Model: {llm_service.model}")
        logger.info(f"   - Streaming: {llm_service.stream_enabled}")
        logger.info(f"   - RAG Threshold: {settings.RAG_DEFAULT_MATCH_THRESHOLD}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    # Yield control (app runs)
    yield

    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info("=" * 80)
    logger.info("VANDA CHATBOT - Shutting down...")
    logger.info("=" * 80)


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="VANDA Chatbot API",
    description="RAG-powered chatbot per Vanda Designers - Interior Design & Architecture",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    lifespan=lifespan
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS - Permetti richieste da agentika.io
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600  # Cache preflight per 1 ora
)


# ============================================================================
# ROUTERS
# ============================================================================

# Chat API
app.include_router(chat_router, prefix="/api", tags=["chat"])

# Voice API
app.include_router(voice_router, prefix="/api", tags=["voice"])


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint - Info API.
    """
    return {
        "service": "VANDA Chatbot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "chat": "POST /api/chat",
            "voice_tts": "POST /api/voice/tts-chunk",
            "health": "GET /health",
            "chat_health": "GET /api/chat/health",
            "stats": "GET /api/chat/stats"
        }
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check principale per Cloud Run.

    Cloud Run usa questo endpoint per verificare che il servizio sia healthy.
    Deve rispondere con 200 OK entro pochi secondi.
    """
    try:
        # Verifica rapida dei servizi
        from app.services.rag_service import rag_service
        from app.services.llm_service import llm_service
        from app.services.memory_manager import memory_manager

        # Check base: servizi inizializzati?
        services_ok = all([
            rag_service is not None,
            llm_service is not None,
            memory_manager is not None
        ])

        if services_ok:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "service": "vanda-chatbot",
                    "version": "1.0.0"
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": "Services not initialized"
                }
            )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handler per 404 Not Found."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "detail": f"Endpoint {request.url.path} non trovato",
            "available_endpoints": [
                "GET /",
                "GET /health",
                "GET /docs",
                "POST /api/chat",
                "POST /api/voice/tts-chunk",
                "GET /api/chat/health",
                "GET /api/chat/stats"
            ]
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handler per 500 Internal Server Error."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "Si è verificato un errore interno del server"
        }
    )


# ============================================================================
# MAIN (per run locale)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting VANDA Chatbot locally...")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Port: 8080")
    logger.info(f"Docs: http://localhost:8080/docs")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,  # Auto-reload per sviluppo
        log_level="info"
    )
