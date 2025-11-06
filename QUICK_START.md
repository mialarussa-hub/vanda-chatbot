# VANDA CHATBOT - QUICK START GUIDE

## PROBLEMI RISOLTI

✅ **Spazi mancanti tra parole** - Fixato parsing SSE token
✅ **Streaming non funziona** - Fixato headers e buffering
✅ **Performance lente** - Ottimizzato RAG e LLM
✅ **Router non registrato** - Attivato endpoint /api/chat

## TEST LOCALE IN 3 PASSI

### 1. Avvia Server
```bash
cd "D:\PROGETTI\AGENTIKA\WEB\vanda-chatbot"
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Test Veloce
```bash
# In un altro terminale:
curl http://localhost:8000/health
```

**✅ Risposta attesa:** `{"status":"healthy",...}`

### 3. Test Streaming
```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Ciao\",\"stream\":true,\"use_rag\":false}"
```

**✅ Deve mostrare:**
```
data: Ciao
data: !
data:  Sono
...
data: [DONE]
```

## TEST AUTOMATICO

```bash
python test_streaming.py
```

**✅ Deve mostrare:** `✅ Total: 4/4 tests passed`

## FILE MODIFICATI

1. **app/main.py** - Registrato router, aggiunto expose_headers
2. **app/api/chat.py** - Fixato parsing spazi, ottimizzato RAG
3. **app/services/llm_service.py** - Aggiunto commenti esplicativi
4. **app/services/rag_service.py** - Aggiunto LIMIT query
5. **app/config.py** - Ridotto max_tokens a 800

## DETTAGLI COMPLETI

Leggi **FIXES_REPORT.md** per:
- Spiegazione tecnica dettagliata
- Istruzioni deployment Cloud Run
- Troubleshooting
- Monitoring e metriche

## PRIMA DI DEPLOY

- [ ] Test locale passati (python test_streaming.py)
- [ ] Verifica .env con credenziali corrette
- [ ] Test manuale streaming con spazi corretti
- [ ] Performance <5 secondi

---
**Ready to deploy!** 🚀
