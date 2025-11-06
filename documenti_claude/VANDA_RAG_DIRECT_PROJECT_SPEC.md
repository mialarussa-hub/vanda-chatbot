# VANDA RAG DIRECT - Specifica Tecnica Completa

## 🎯 OBIETTIVO DEL PROGETTO

Sostituire l'attuale architettura n8n (lenta) con un sistema Python/FastAPI diretto che:
- Riceve richieste dal frontend via API
- Dialoga direttamente con ChatGPT (OpenAI)
- Implementa RAG con Supabase Vector Database
- Mantiene memoria conversazionale
- Restituisce risposte in streaming real-time
- Deploy su Railway.app

### Problema Attuale
```
Frontend → Webhook n8n → Extract Input → AI Agent Master → 
  → Tool Workflow "AGENTE RAG" → AI Agent secondario → 
    → Supabase Vector Search + Embeddings + Reranker → 
      → PostgreSQL Memory → OpenAI → Risposta

LATENZA TOTALE: 10-30 secondi
```

### Soluzione Target
```
Frontend → FastAPI Endpoint → 
  → [Parallelo] Supabase Vector Search + OpenAI Streaming →
    → Risposta real-time con streaming

LATENZA TARGET: 2-5 secondi
```

---

## 📚 STACK TECNOLOGICO

### Backend
- **Python 3.11+**
- **FastAPI** - Web framework asincrono
- **Uvicorn** - ASGI server
- **OpenAI Python SDK** - Per GPT-4/3.5 con streaming
- **Supabase Python Client** - Per vector database
- **Langchain** - (opzionale) Per RAG orchestration
- **Redis** o **In-Memory Dict** - Per session memory

### Deployment
- **Railway.app** - Hosting
- **Docker** - Containerizzazione
- **GitHub** - Version control + CI/CD automatico

---

## 🏗️ ARCHITETTURA DEL SISTEMA

### Componenti Principali

```
┌─────────────────────────────────────────────────────┐
│                  FRONTEND (Esistente)                │
│              (Invia richieste HTTP POST)             │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              FASTAPI APPLICATION                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  POST /api/chat                              │  │
│  │  - Riceve: message, session_id, user_id     │  │
│  │  - Restituisce: StreamingResponse           │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  Memory Manager                              │  │
│  │  - Gestisce history per session_id          │  │
│  │  - In-memory o Redis                        │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  RAG Pipeline                                │  │
│  │  1. Genera embedding della query            │  │
│  │  2. Query Supabase vector DB                │  │
│  │  3. Recupera top-k documenti rilevanti      │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  LLM Orchestrator                            │  │
│  │  - Costruisce prompt con context            │  │
│  │  - Chiama OpenAI con streaming              │  │
│  │  - Gestisce memoria conversazionale         │  │
│  └──────────────────────────────────────────────┘  │
└────────────┬───────────────────┬───────────────────┘
             │                   │
             ▼                   ▼
    ┌────────────────┐  ┌────────────────┐
    │  OpenAI API    │  │  Supabase DB   │
    │  (GPT-4)       │  │  (Vector Store)│
    └────────────────┘  └────────────────┘
```

---

## 📁 STRUTTURA DEL PROGETTO

```
vanda-rag-direct/
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # Entry point FastAPI
│   ├── config.py                # Configurazione e env vars
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── chat.py              # Endpoint /api/chat
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── memory_manager.py    # Gestione memoria conversazionale
│   │   ├── rag_service.py       # RAG pipeline con Supabase
│   │   ├── llm_service.py       # Integrazione OpenAI
│   │   └── embedding_service.py # Generazione embeddings
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic models
│   │
│   └── utils/
│       ├── __init__.py
│       └── logging.py           # Logging configurato
│
├── tests/
│   ├── __init__.py
│   ├── test_chat.py
│   └── test_rag.py
│
├── .env.example                 # Template variabili ambiente
├── .gitignore
├── Dockerfile                   # Container config
├── docker-compose.yml           # Local development
├── requirements.txt             # Python dependencies
├── railway.json                 # Railway config
└── README.md                    # Documentazione
```

---

## 🔌 API ENDPOINTS

### 1. POST /api/chat
**Descrizione**: Endpoint principale per chat con RAG

**Request Body**:
```json
{
  "message": "Come funziona il vostro servizio di progettazione?",
  "session_id": "uuid-della-sessione",
  "user_id": "user-123",
  "stream": true
}
```

**Response** (Streaming):
```
data: {"type": "token", "content": "Certo"}
data: {"type": "token", "content": ","}
data: {"type": "token", "content": " posso"}
data: {"type": "token", "content": " aiutarti"}
...
data: {"type": "done", "full_response": "...", "sources": [...]}
```

**Headers**:
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`

### 2. GET /api/chat/history/{session_id}
**Descrizione**: Recupera cronologia conversazione

**Response**:
```json
{
  "session_id": "uuid",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ]
}
```

### 3. DELETE /api/chat/history/{session_id}
**Descrizione**: Cancella memoria conversazione

### 4. GET /health
**Descrizione**: Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "openai": "connected",
  "supabase": "connected"
}
```

---

## 🗄️ INTEGRAZIONE SUPABASE

### Configurazione Vector Store

**Tabella Esistente**: (da confermare con utente)
```sql
-- Struttura attesa (standard Supabase vector)
CREATE TABLE documents (
  id BIGSERIAL PRIMARY KEY,
  content TEXT,
  metadata JSONB,
  embedding VECTOR(1536)  -- OpenAI text-embedding-3-small
);

-- Index per similarity search
CREATE INDEX ON documents 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Query Vector Similarity

```python
# Pseudo-codice per similarity search
def search_similar_documents(query_embedding: list[float], top_k: int = 5):
    """
    Cerca documenti simili usando cosine similarity
    """
    result = supabase.rpc(
        'match_documents',  # Stored procedure Supabase
        {
            'query_embedding': query_embedding,
            'match_count': top_k,
            'match_threshold': 0.7  # Threshold similarità minima
        }
    )
    return result.data
```

### Stored Procedure Supabase (se non esiste)
```sql
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 5,
  match_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
  id BIGINT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

---

## 🧠 GESTIONE MEMORIA CONVERSAZIONALE

### Opzione 1: In-Memory (Semplice, per iniziare)
```python
# Struttura in-memory
conversations = {
    "session-uuid-123": {
        "messages": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ],
        "created_at": datetime,
        "last_activity": datetime
    }
}

# Cleanup automatico delle sessioni vecchie (> 24h)
```

### Opzione 2: Redis (Produzione, scalabile)
```python
# Key structure
# Key: session:{session_id}
# Value: JSON serialized list of messages
# TTL: 24 hours
```

### Context Window Management
- Mantenere ultimi **10 messaggi** (5 user + 5 assistant)
- Se superato limite tokens (8k per GPT-4), riassumere conversazione precedente
- Includere sempre context RAG aggiornato

---

## 🤖 INTEGRAZIONE OPENAI

### Modello Consigliato
- **GPT-4-turbo** (128k context, veloce)
- **GPT-3.5-turbo** (fallback, più economico)

### Streaming Implementation
```python
# Esempio streaming
async def stream_openai_response(messages: list, context: str):
    response = await openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context: {context}"},
            *messages
        ],
        stream=True,
        temperature=0.7,
        max_tokens=1000
    )
    
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

### System Prompt (Template)
```
Sei VANDA, un assistente virtuale esperto in [DOMINIO AZIENDA].

Il tuo compito è rispondere alle domande degli utenti utilizzando 
ESCLUSIVAMENTE le informazioni fornite nel contesto.

Se non trovi informazioni nel contesto, rispondi con:
"Mi dispiace, non ho informazioni sufficienti per rispondere. 
Posso metterti in contatto con un nostro esperto?"

Rispondi in modo:
- Professionale ma amichevole
- Conciso (max 150 parole)
- Preciso e basato sui fatti
- In italiano

CONTESTO DISPONIBILE:
{context}

CONVERSAZIONE PRECEDENTE:
{history}
```

---

## 🔄 FLUSSO COMPLETO RICHIESTA

```
1. Frontend → POST /api/chat
   Body: {message, session_id}

2. FastAPI riceve richiesta
   ↓
3. Memory Manager: Carica history da session_id
   ↓
4. Embedding Service: Genera embedding del message
   query_embedding = openai.embeddings.create(
       model="text-embedding-3-small",
       input=message
   )
   ↓
5. RAG Service: Query Supabase vector DB
   relevant_docs = supabase.rpc('match_documents', {
       query_embedding: query_embedding,
       match_count: 5
   })
   ↓
6. Context Builder: Prepara context string
   context = "\n\n".join([doc.content for doc in relevant_docs])
   ↓
7. LLM Service: Costruisce messages array
   messages = [
       {"role": "system", "content": SYSTEM_PROMPT},
       {"role": "user", "content": f"Context: {context}"},
       *conversation_history,
       {"role": "user", "content": message}
   ]
   ↓
8. OpenAI Streaming: Invia a GPT-4
   async for token in openai.chat.completions.create(...):
       yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
   ↓
9. Memory Manager: Salva messaggio in session_id
   ↓
10. Response: Stream completo al frontend
```

---

## ⚙️ CONFIGURAZIONE E VARIABILI D'AMBIENTE

### File .env (da creare)
```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_TABLE_NAME=documents

# App Config
ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=8000

# CORS
ALLOWED_ORIGINS=https://tuosito.com,https://www.tuosito.com

# Memory
MEMORY_TYPE=in_memory  # o "redis"
REDIS_URL=redis://localhost:6379  # se usi Redis

# Rate Limiting (opzionale)
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60  # secondi
```

---

## 📦 DIPENDENZE (requirements.txt)

```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# OpenAI
openai==1.3.0

# Supabase
supabase==2.0.3

# Embeddings & Vector
numpy==1.24.3

# Environment & Config
python-dotenv==1.0.0
pydantic==2.4.2
pydantic-settings==2.0.3

# Async & Utilities
httpx==0.25.0
aiohttp==3.9.0

# Memory (opzionale)
redis==5.0.1

# Monitoring & Logging
loguru==0.7.2

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
```

---

## 🐳 DOCKERFILE

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY ./app ./app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🚂 DEPLOYMENT SU RAILWAY

### 1. Setup Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init
```

### 2. File railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 3. Configurazione Variabili Railway
```bash
# Aggiungi variabili nel Railway Dashboard
railway variables set OPENAI_API_KEY=sk-...
railway variables set SUPABASE_URL=https://...
railway variables set SUPABASE_KEY=eyJ...
```

### 4. Deploy
```bash
# Deploy automatico
railway up

# Il sistema genererà un URL tipo:
# https://vanda-rag-direct-production.up.railway.app
```

---

## 🧪 TESTING

### Test Endpoint Locale
```bash
# Avvia server
uvicorn app.main:app --reload

# Test con curl
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Ciao, come funziona il servizio?",
    "session_id": "test-123",
    "stream": true
  }'
```

### Test Streaming
```bash
# Test streaming con httpie
http --stream POST localhost:8000/api/chat \
  message="Test" \
  session_id="test-456" \
  stream:=true
```

---

## 📊 MONITORAGGIO & LOGGING

### Logging Structure
```python
# Logs da includere
- Request ID per ogni chiamata
- Session ID
- User ID (se disponibile)
- Latency per ogni step:
  * Embedding generation time
  * Vector search time
  * OpenAI response time
  * Total request time
- Error tracking
- Token usage (cost tracking)
```

### Metriche da Tracciare
```
- Requests per second
- Average response time
- P95/P99 latency
- Error rate
- Token consumption
- Cache hit rate (se implementi caching)
```

---

## 🔒 SICUREZZA

### Checklist
- [ ] Validazione input (max length, sanitization)
- [ ] Rate limiting per IP/session
- [ ] API key rotation mechanism
- [ ] CORS configurato correttamente
- [ ] HTTPS enforced
- [ ] Secrets in environment variables (no hardcode)
- [ ] Input validation per SQL injection prevention
- [ ] Timeout configurati (no hanging requests)

---

## 🎯 PRIORITÀ IMPLEMENTAZIONE

### Phase 1 - MVP (Core Functionality)
1. ✅ Setup FastAPI base + health endpoint
2. ✅ Integrazione OpenAI (no streaming per ora)
3. ✅ Integrazione Supabase vector search
4. ✅ Endpoint /api/chat base (no memory)
5. ✅ Deploy su Railway

### Phase 2 - Memory & Streaming
6. ✅ Implementa memoria in-memory
7. ✅ Abilita streaming OpenAI
8. ✅ Gestione errori e retry logic

### Phase 3 - Production Ready
9. ✅ Logging e monitoring
10. ✅ Rate limiting
11. ✅ Testing suite
12. ✅ Redis per memoria (opzionale)

---

## 🔗 INTEGRAZIONE FRONTEND

### Modifiche Necessarie Frontend

**Vecchio endpoint n8n**:
```javascript
// VECCHIO
const response = await fetch('https://n8n.example.com/webhook/vanda-rag', {
  method: 'POST',
  body: JSON.stringify({ message })
});
```

**Nuovo endpoint FastAPI**:
```javascript
// NUOVO - Streaming
const response = await fetch('https://vanda-rag.railway.app/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: userMessage,
    session_id: sessionId,  // Genera UUID se nuova sessione
    stream: true
  })
});

// Gestione streaming
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.type === 'token') {
        appendToChat(data.content);  // Aggiungi token alla UI
      }
    }
  }
}
```

---

## 📝 NOTE AGGIUNTIVE

### Performance Target
- Primo token: < 2 secondi
- Risposta completa: < 5 secondi (vs 10-30 sec attuali)
- Throughput: 10-50 req/sec

### Costi Stimati
- OpenAI: ~$0.01 per richiesta (GPT-4)
- Railway: ~$10-20/mese (base)
- Supabase: Free tier OK per start

### Scalabilità
- Attuale design: fino a 1000 req/min
- Per scale maggiore: aggiungi Redis + Load Balancer

---

## ✅ CHECKLIST FINALE PRE-DEPLOY

- [ ] Tutte le dipendenze in requirements.txt
- [ ] Dockerfile validato
- [ ] .env.example creato
- [ ] Variabili Railway configurate
- [ ] Health endpoint funzionante
- [ ] Test locale completato
- [ ] CORS configurato per dominio produzione
- [ ] Logging abilitato
- [ ] Error handling implementato
- [ ] README.md aggiornato

---

## 🚀 NEXT STEPS

1. **Claude Code** implementa il codice base
2. **Testing locale** con le tue credenziali reali
3. **Deploy su Railway**
4. **Test integrazione frontend**
5. **Monitoring primi giorni**
6. **Iterazione ottimizzazioni**

---

## 📞 INFORMAZIONI DA RICHIEDERE ALL'UTENTE

Prima di iniziare l'implementazione, confermare:

1. **OpenAI API Key** - Per GPT-4
2. **Supabase URL e Key** - Per vector database
3. **Nome tabella Supabase** - Dove sono i documenti vettorizzati
4. **Struttura tabella** - Schema columns (content, metadata, embedding)
5. **Dominio frontend** - Per configurare CORS
6. **System prompt personalizzato** - Personalità VANDA
7. **Preferenze modello** - GPT-4 o GPT-3.5-turbo?

---

## 📚 RISORSE UTILI

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [Supabase Python Client](https://github.com/supabase-community/supabase-py)
- [Railway Docs](https://docs.railway.app/)
- [Streaming Response Guide](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)

---

**FINE DOCUMENTO**

> 🎯 Questo documento contiene tutte le informazioni necessarie per implementare il sistema VANDA RAG Direct. Claude Code può partire immediatamente con l'implementazione seguendo questa specifica.
