# VANDA Chatbot - RAG-powered AI Assistant

Chatbot intelligente per **Vanda Designers** (studio di architettura e interior design in Spagna) con RAG (Retrieval-Augmented Generation), streaming SSE, e persistenza conversazioni su Supabase.

---

## Caratteristiche

✅ **RAG (Retrieval-Augmented Generation)**
- Ricerca semantica su 337 documenti in Supabase
- Embeddings con OpenAI `text-embedding-3-small`
- Filtri avanzati (category, project_type, priority, brand, client)
- Similarity threshold configurabile

✅ **Streaming SSE (Server-Sent Events)**
- Risposta token-by-token in tempo reale
- Time-to-First-Token (TTFT): ~600ms
- 8x miglioramento percezione velocità

✅ **Memory Manager**
- Persistenza conversazioni su Supabase PostgreSQL
- History recuperabile per session_id
- Statistiche e analytics per sessione
- Thread-safe con lock

✅ **Ottimizzato per Performance**
- Modello: `gpt-4o-mini` (veloce ed economico)
- Max tokens: 500 (risposte concise)
- RAG match count: 3 documenti (ottimale)
- Temperature: 0.5 (bilanciato)

✅ **Production-Ready**
- FastAPI con CORS per agentika.io
- Dockerfile per Google Cloud Run
- Health checks e monitoring
- Error handling robusto
- Logging strutturato con loguru

---

## Architettura

```
┌──────────────────────────────────────────┐
│           Frontend (agentika.io)         │
│           React/Next.js                  │
└────────────────┬─────────────────────────┘
                 │ HTTPS/SSE
                 │ POST /api/chat
┌────────────────▼─────────────────────────┐
│      Google Cloud Run (FastAPI)          │
│  ┌────────────────────────────────────┐  │
│  │  main.py                           │  │
│  │  ├─ Chat API (app/api/chat.py)    │  │
│  │  ├─ RAG Service                    │  │
│  │  ├─ LLM Service (streaming)        │  │
│  │  ├─ Memory Manager                 │  │
│  │  └─ Embedding Service              │  │
│  └────────────────────────────────────┘  │
└────────────────┬─────────────────────────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
  ┌────────┐ ┌────────┐ ┌──────────┐
  │Supabase│ │OpenAI  │ │Supabase  │
  │(docs)  │ │API     │ │(chats)   │
  └────────┘ └────────┘ └──────────┘
```

---

## Setup Locale

### 1. Prerequisiti
- Python 3.11+
- Account OpenAI con API key
- Account Supabase con progetto creato

### 2. Clone & Install
```bash
cd D:\PROGETTI\AGENTIKA\WEB\vanda-chatbot

# Crea virtual environment
python -m venv venv

# Attiva venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Installa dipendenze
pip install -r requirements.txt
```

### 3. Configura `.env`
Copia `.env.example` in `.env` e configura:

```env
# OpenAI
OPENAI_API_KEY=sk-proj-...

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGci...
SUPABASE_TABLE_NAME=documents

# CORS
ALLOWED_ORIGINS=["https://www.agentika.io","https://agentika.io","http://localhost:3000"]

# App
ENV=development
LOG_LEVEL=INFO

# RAG
RAG_DEFAULT_MATCH_COUNT=3
RAG_DEFAULT_MATCH_THRESHOLD=0.60

# LLM
LLM_DEFAULT_MODEL=gpt-4o-mini
LLM_DEFAULT_TEMPERATURE=0.5
LLM_MAX_TOKENS=500
LLM_STREAM_ENABLED=true
```

### 4. Setup Database Supabase

Crea le tabelle necessarie:

```sql
-- Tabella documenti (RAG)
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_embedding ON documents
USING ivfflat (embedding vector_cosine_ops);

-- Tabella chat messages (Memory)
CREATE TABLE chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session_created
ON chat_messages(session_id, created_at DESC);
```

---

## Run Locale

### Avvia FastAPI server
```bash
uvicorn main:app --reload --port 8080
```

Oppure:
```bash
python main.py
```

### Test endpoints

**Health check:**
```bash
curl http://localhost:8080/health
```

**Chat (non-streaming):**
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Parlami dei vostri servizi",
    "stream": false
  }'
```

**Chat (streaming):**
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quali sono i tempi di realizzazione?",
    "stream": true
  }'
```

---

## Testing

### Test singoli servizi

```bash
# RAG Service
python test_rag_simple.py

# LLM Service + Streaming
python test_llm_streaming.py

# Memory Manager
python test_memory_simple.py
```

### Test end-to-end

```bash
# 1. Avvia server
uvicorn main:app --port 8080

# 2. In un altro terminale, run test
python test_chatbot_e2e.py
```

Output atteso:
```
✅ App running & health check
✅ Chat non-streaming con RAG
✅ Chat streaming con RAG
✅ Verifica history su DB
✅ Statistiche sessione
✅ Health check servizi
✅ Chat senza RAG
✅ Cleanup sessione test

🎉 CHATBOT FUNZIONANTE E PRONTO PER IL DEPLOY!
```

---

## Deploy su Google Cloud Run

Vedi guida completa: **[DEPLOY.md](DEPLOY.md)**

### Deploy rapido

```bash
# 1. Autentica
gcloud auth login

# 2. Configura progetto
gcloud config set project TUO_PROJECT_ID

# 3. Deploy (con secrets già configurati)
gcloud run deploy vanda-chatbot \
  --source . \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-secrets "OPENAI_API_KEY=openai-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest"
```

---

## API Endpoints

### `POST /api/chat`
Endpoint principale del chatbot.

**Request Body:**
```json
{
  "message": "Parlami dei vostri progetti residenziali",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "stream": true,
  "use_rag": true,
  "include_sources": false
}
```

**Response (stream=false):**
```json
{
  "session_id": "550e8400-...",
  "message": "Ciao! Siamo specializzati in interior design residenziale...",
  "metadata": {
    "tokens_used": 450,
    "processing_time_ms": 1234,
    "model": "gpt-4o-mini",
    "rag_enabled": true,
    "documents_found": 3
  }
}
```

### Altri Endpoints
- `GET /health` - Health check principale
- `GET /api/chat/health` - Health check servizi
- `GET /api/chat/stats` - Statistiche sessioni

---

## Integrazione Frontend

Esempio React/Next.js in [README.md completo](README.md).

---

## Performance

- **TTFT**: ~600ms
- **Risposta completa**: 3-5s
- **RAG search**: <200ms
- **Modello**: gpt-4o-mini (ottimizzato)

---

## Costi Stimati

- **OpenAI (10k richieste/mese)**: ~$5-10
- **Cloud Run (10k richieste/mese)**: ~$2-3
- **Supabase**: Free tier / $25/mese Pro

**Totale: $10-15/mese** 🎉

---

## Struttura Progetto

```
vanda-chatbot/
├── app/
│   ├── config.py
│   ├── models/schemas.py
│   ├── services/
│   │   ├── rag_service.py
│   │   ├── llm_service.py
│   │   ├── memory_manager.py
│   │   └── embedding_service.py
│   └── api/chat.py
├── main.py
├── Dockerfile
├── requirements.txt
├── test_chatbot_e2e.py
├── DEPLOY.md
└── README.md
```

---

## Supporto

- **Logs Cloud Run**: `gcloud run services logs tail vanda-chatbot`
- **Health check**: `curl YOUR_URL/health`
- **Docs**: Vedi [DEPLOY.md](DEPLOY.md)

---

**🚀 Realizzato con Claude Code da Anthropic**
