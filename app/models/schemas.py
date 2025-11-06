"""
Pydantic models per VANDA chatbot.

Definisce tutti i modelli per:
- Request/Response API
- Modelli RAG e documenti
- Conversazioni e messaggi
- Filtri e metadata
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class MessageRole(str, Enum):
    """Ruoli possibili per i messaggi"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class StreamTokenType(str, Enum):
    """Tipi di token per lo streaming"""
    TOKEN = "token"
    SOURCES = "sources"
    DONE = "done"
    ERROR = "error"


class ClientType(str, Enum):
    """Tipi di clienti per i progetti"""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    HOSPITALITY = "hospitality"
    RETAIL = "retail"


class ProjectScale(str, Enum):
    """Scala dei progetti"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Visibility(str, Enum):
    """Livelli di visibilità"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================================
# MODELLI METADATA E DOCUMENTI
# ============================================================================

class DocumentMetadata(BaseModel):
    """
    Metadata specifici per documenti Vanda Designers.

    Rappresenta la struttura JSONB del campo 'metadata' nel database Supabase.
    """
    id: Optional[str] = Field(None, description="ID univoco chunk (formato: url#chunk0)")
    url: Optional[str] = Field(None, description="URL sorgente documento")
    heading: Optional[str] = Field(None, description="Titolo/heading del progetto")
    tags: Optional[str] = Field(None, description="Tags comma-separated")
    category: Optional[str] = Field(None, description="Categoria principale (es: portfolio)")
    subcategory: Optional[str] = Field(None, description="Sottocategoria (es: interior)")
    document_type: Optional[str] = Field(None, description="Tipo documento (es: progetto)")
    client: Optional[str] = Field(None, description="Nome cliente")
    client_type: Optional[str] = Field(None, description="Tipo cliente (residential/commercial/etc)")
    brand: Optional[str] = Field(None, description="Brand associato")
    visibility: Optional[str] = Field(None, description="Livello visibilità (high/medium/low)")
    priority: Optional[int] = Field(None, ge=0, le=5, description="Priorità 0-5 (5=massima)")
    featured: Optional[bool] = Field(None, description="Progetto in evidenza")
    project_scale: Optional[str] = Field(None, description="Scala progetto (small/medium/large)")
    chunk_number: Optional[int] = Field(None, ge=0, description="Numero chunk corrente")
    total_chunk: Optional[int] = Field(None, ge=1, description="Totale chunks documento")
    document_id: Optional[str] = Field(None, description="ID documento originale")
    source: Optional[str] = Field(None, description="Sorgente dati (es: blob)")
    blobType: Optional[str] = Field(None, description="MIME type blob")
    loc: Optional[Dict[str, Any]] = Field(None, description="Location info (linee)")

    class Config:
        extra = "allow"  # Permetti campi extra non definiti
        use_enum_values = True


class DocumentChunk(BaseModel):
    """
    Rappresentazione di un chunk di documento recuperato dal database.

    Corrisponde a un record della tabella 'documents' con similarity score.
    """
    id: int = Field(..., description="ID primario database")
    content: str = Field(..., description="Contenuto testuale del chunk")
    metadata: DocumentMetadata = Field(..., description="Metadata JSONB")
    similarity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Cosine similarity score")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "content": "Interior Design di un appartamento nel Cuore di Burgos...",
                "metadata": {
                    "heading": "Interior Design Burgos",
                    "category": "portfolio",
                    "client_type": "residential",
                    "tags": "interior design, ristrutturazione"
                },
                "similarity": 0.87
            }
        }


class MetadataFilter(BaseModel):
    """
    Filtri opzionali per la ricerca RAG.

    Permette di filtrare i documenti per metadata specifici durante
    la similarity search.
    """
    category: Optional[str] = Field(None, description="Filtra per categoria")
    subcategory: Optional[str] = Field(None, description="Filtra per sottocategoria")
    client: Optional[str] = Field(None, description="Filtra per nome cliente")
    client_type: Optional[str] = Field(None, description="Filtra per tipo cliente")
    brand: Optional[str] = Field(None, description="Filtra per brand")
    visibility: Optional[str] = Field(None, description="Filtra per visibilità")
    featured: Optional[bool] = Field(None, description="Solo progetti featured")
    min_priority: Optional[int] = Field(None, ge=0, le=5, description="Priorità minima (0-5)")
    project_scale: Optional[str] = Field(None, description="Scala progetto")
    document_type: Optional[str] = Field(None, description="Tipo documento")

    class Config:
        json_schema_extra = {
            "example": {
                "category": "portfolio",
                "client_type": "residential",
                "featured": True,
                "min_priority": 5
            }
        }


# ============================================================================
# MODELLI CONVERSAZIONALI
# ============================================================================

class Message(BaseModel):
    """
    Singolo messaggio in una conversazione.
    """
    role: MessageRole = Field(..., description="Ruolo mittente (user/assistant/system)")
    content: str = Field(..., min_length=1, description="Contenuto messaggio")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp creazione")

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Parlami dei vostri progetti di interior design",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }


class ConversationHistory(BaseModel):
    """
    Storia completa di una conversazione.

    Mantiene tutti i messaggi di una sessione con metadata temporali.
    """
    session_id: str = Field(..., description="UUID sessione")
    messages: List[Message] = Field(default_factory=list, description="Lista messaggi ordinati")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creazione conversazione")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Ultimo aggiornamento")
    user_id: Optional[str] = Field(None, description="ID utente (opzionale)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata aggiuntivi")

    def add_message(self, role: MessageRole, content: str) -> None:
        """Aggiunge un messaggio alla storia"""
        self.messages.append(Message(role=role, content=content))
        self.updated_at = datetime.utcnow()

    def get_recent_messages(self, count: int = 5) -> List[Message]:
        """Ritorna gli ultimi N messaggi"""
        return self.messages[-count:]

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "messages": [
                    {"role": "user", "content": "Ciao"},
                    {"role": "assistant", "content": "Benvenuto su Vanda Designers!"}
                ],
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:30:00Z"
            }
        }


# ============================================================================
# MODELLI API REQUEST/RESPONSE
# ============================================================================

class ChatRequest(BaseModel):
    """
    Request per endpoint chat.

    Contiene messaggio utente, identificatori sessione e opzioni streaming.
    """
    message: str = Field(..., min_length=1, max_length=2000, description="Messaggio utente")
    session_id: str = Field(..., description="UUID sessione chat")
    user_id: Optional[str] = Field(None, description="ID utente (opzionale)")
    stream: bool = Field(True, description="Abilita streaming response")
    metadata_filters: Optional[MetadataFilter] = Field(None, description="Filtri RAG opzionali")
    max_context_docs: Optional[int] = Field(5, ge=1, le=20, description="Max documenti context")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Temperature LLM")

    @validator("message")
    def message_not_empty(cls, v):
        """Valida che il messaggio non sia vuoto"""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Quali sono i vostri progetti di interior design più recenti?",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "stream": True,
                "metadata_filters": {
                    "category": "portfolio",
                    "featured": True
                },
                "max_context_docs": 5
            }
        }


class ChatResponse(BaseModel):
    """
    Response per endpoint chat (modalità non-streaming).

    Contiene risposta LLM, documenti sorgente e metadata.
    """
    response: str = Field(..., description="Risposta generata dall'LLM")
    sources: List[DocumentChunk] = Field(default_factory=list, description="Documenti sorgente usati")
    session_id: str = Field(..., description="UUID sessione")
    tokens_used: Optional[int] = Field(None, description="Token consumati (se disponibile)")
    processing_time_ms: Optional[float] = Field(None, description="Tempo elaborazione in ms")
    model: Optional[str] = Field(None, description="Modello LLM usato")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "Ecco i nostri progetti più recenti...",
                "sources": [
                    {
                        "id": 123,
                        "content": "Progetto interior design...",
                        "metadata": {"heading": "Burgos Interior"},
                        "similarity": 0.89
                    }
                ],
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "tokens_used": 450,
                "processing_time_ms": 1234.5,
                "model": "gpt-4"
            }
        }


class StreamToken(BaseModel):
    """
    Token singolo per streaming response.

    Può contenere:
    - Token di testo incrementale
    - Lista documenti sorgente
    - Segnale di completamento
    - Errore
    """
    type: StreamTokenType = Field(..., description="Tipo token stream")
    content: Optional[str] = Field(None, description="Contenuto token (per type=token)")
    sources: Optional[List[DocumentChunk]] = Field(None, description="Documenti (per type=sources)")
    error: Optional[str] = Field(None, description="Messaggio errore (per type=error)")
    done: Optional[bool] = Field(None, description="Flag completamento (per type=done)")

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "examples": [
                {
                    "type": "token",
                    "content": "Ecco "
                },
                {
                    "type": "sources",
                    "sources": [{"id": 123, "content": "...", "metadata": {}, "similarity": 0.89}]
                },
                {
                    "type": "done",
                    "done": True
                }
            ]
        }


# ============================================================================
# MODELLI HEALTH CHECK E STATUS
# ============================================================================

class HealthCheck(BaseModel):
    """Response health check endpoint"""
    status: str = Field(..., description="Status applicazione")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: Optional[str] = Field(None, description="Versione API")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-01-15T10:00:00Z",
                "version": "1.0.0"
            }
        }


class ErrorResponse(BaseModel):
    """Response standardizzata per errori"""
    error: str = Field(..., description="Tipo errore")
    message: str = Field(..., description="Messaggio errore dettagliato")
    detail: Optional[Dict[str, Any]] = Field(None, description="Dettagli aggiuntivi")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Message cannot be empty",
                "detail": {"field": "message"},
                "timestamp": "2025-01-15T10:00:00Z"
            }
        }
