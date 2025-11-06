from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_TABLE_NAME: str = "documents"

    # CORS - Configurato per agentika.io e sviluppo locale
    ALLOWED_ORIGINS: List[str] = [
        "https://www.agentika.io",
        "https://agentika.io",
        "http://localhost:3000",  # Per sviluppo locale
        "http://localhost:8000",  # Backend locale
        "http://127.0.0.1:8000",  # Backend locale (IP)
        "null"  # Per file HTML aperti direttamente (file://)
    ]

    # App Config
    LOG_LEVEL: str = "INFO"
    ENV: str = "production"

    # RAG Configuration
    RAG_DEFAULT_MATCH_COUNT: int = 5
    RAG_DEFAULT_MATCH_THRESHOLD: float = 0.75
    RAG_MAX_CONTEXT_LENGTH: int = 8000
    RAG_ENABLE_METADATA_FILTERS: bool = True

    # LLM Configuration
    LLM_DEFAULT_MODEL: str = "gpt-4"
    LLM_DEFAULT_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 800  # Ridotto per performance (risposte più concise)
    LLM_STREAM_ENABLED: bool = True

    # TTS (Text-to-Speech) Configuration
    OPENAI_TTS_VOICE: str = "nova"  # Voices: alloy, echo, fable, onyx, nova, shimmer
    OPENAI_TTS_MODEL: str = "tts-1"  # Models: tts-1 (standard), tts-1-hd (high quality)
    OPENAI_TTS_SPEED: float = 1.0  # Speech speed: 0.25 - 4.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
