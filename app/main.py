from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import chat, voice

app = FastAPI(title="VANDA RAG Chatbot", version="1.0.0")

# CORS configuration per www.agentika.io
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "vanda-rag-chatbot"
    }

# Include API routers
app.include_router(chat.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
