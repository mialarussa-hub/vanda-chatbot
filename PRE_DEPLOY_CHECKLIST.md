# PRE-DEPLOY CHECKLIST - VANDA Chatbot

**Data:** ___________
**Deployer:** ___________
**Target:** Google Cloud Run

---

## 1. TEST LOCALE

### A. Ambiente
- [ ] Virtual environment attivato (`.\venv\Scripts\activate`)
- [ ] Dipendenze installate (`pip install -r requirements.txt`)
- [ ] File `.env` presente con tutte le variabili:
  - [ ] `OPENAI_API_KEY`
  - [ ] `SUPABASE_URL`
  - [ ] `SUPABASE_KEY`
  - [ ] `SUPABASE_TABLE_NAME`

### B. Server Locale
- [ ] Server si avvia senza errori: `uvicorn app.main:app --reload`
- [ ] Nessun errore nei log all'avvio
- [ ] Log mostra: `INFO - LLM Service initialized`
- [ ] Log mostra: `INFO - RAG Service initialized`

### C. Health Checks
```bash
curl http://localhost:8000/health
```
- [ ] Risposta 200 OK
- [ ] JSON contiene `"status": "healthy"`

```bash
curl http://localhost:8000/api/chat/health
```
- [ ] Risposta 200 OK
- [ ] Tutti i servizi sono `true`:
  - [ ] `"rag_service": true`
  - [ ] `"llm_service": true`
  - [ ] `"memory_manager": true`
  - [ ] `"embedding_service": true`

### D. Test Streaming
```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Ciao","stream":true,"use_rag":false}'
```
- [ ] Risposta inizia subito (entro 2 secondi)
- [ ] Token arrivano uno alla volta (formato `data: ...`)
- [ ] **CRITICO:** Ci sono spazi tra le parole (NON "Ciaosono" ma "Ciao sono")
- [ ] Termina con `data: [DONE]`
- [ ] Tempo totale <5 secondi

### E. Test Non-Streaming
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Cosa fate?","stream":false,"use_rag":false}'
```
- [ ] Risposta JSON completa
- [ ] Contiene `session_id`, `message`, `metadata`
- [ ] Testo ha spazi corretti
- [ ] Tempo <5 secondi

### F. Test RAG
```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Parlami dei progetti","stream":true,"use_rag":true}'
```
- [ ] Risposta contestuale (usa info da database)
- [ ] Log mostra: `Found X relevant documents`
- [ ] Risposta pertinente alla domanda
- [ ] Tempo <8 secondi (RAG è più lento)

### G. Test Script Automatico
```bash
python test_streaming.py
```
- [ ] Tutti i test passano: `✅ Total: 4/4 tests passed`
- [ ] Nessun errore nel log
- [ ] Metriche accettabili:
  - [ ] First chunk time <2s
  - [ ] Total time <5s
  - [ ] Spaces preserved: True

---

## 2. CODICE E CONFIGURAZIONE

### A. Modifiche Verificate
- [ ] `app/main.py`: Router registrato (riga 4, 26)
- [ ] `app/api/chat.py`: Fix spazi (riga 286: `chunk[6:-2]`)
- [ ] `app/api/chat.py`: Headers streaming (riga 321: `Transfer-Encoding`)
- [ ] `app/config.py`: Max tokens ridotto (riga 33: `800`)
- [ ] `app/services/rag_service.py`: Query limit (riga 117)

### B. Logs e Debug
- [ ] Nessun `print()` statement (usa `logger`)
- [ ] Log level in production: `INFO` o `WARNING`
- [ ] Nessun log di dati sensibili (API keys, ecc.)

### C. Sicurezza
- [ ] `.env` NON è in git (verificare `.gitignore`)
- [ ] Nessuna API key hardcoded nel codice
- [ ] CORS configurato solo per domini autorizzati
- [ ] Validazione input utente attiva

---

## 3. DOCKER

### A. Build Locale
```bash
docker build -t vanda-chatbot .
```
- [ ] Build completa senza errori
- [ ] Image size ragionevole (<500MB)

### B. Test Docker Locale
```bash
docker run -p 8000:8000 --env-file .env vanda-chatbot
```
- [ ] Container si avvia
- [ ] Health check risponde: `curl http://localhost:8000/health`
- [ ] Chat funziona: `curl -N -X POST http://localhost:8000/api/chat ...`
- [ ] Log visibili con `docker logs`

---

## 4. GOOGLE CLOUD RUN

### A. Pre-Deploy
- [ ] Progetto GCP configurato
- [ ] `gcloud` CLI installato e autenticato
- [ ] Variabili ambiente preparate:
  ```bash
  export OPENAI_API_KEY="sk-..."
  export SUPABASE_URL="https://..."
  export SUPABASE_KEY="eyJ..."
  ```

### B. Deploy
```bash
gcloud run deploy vanda-chatbot \
  --source . \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "OPENAI_API_KEY=$OPENAI_API_KEY,SUPABASE_URL=$SUPABASE_URL,SUPABASE_KEY=$SUPABASE_KEY"
```
- [ ] Deploy completato senza errori
- [ ] URL Cloud Run ottenuto
- [ ] Service status: `SERVING`

### C. Post-Deploy Verification
```bash
SERVICE_URL=$(gcloud run services describe vanda-chatbot --region europe-west1 --format 'value(status.url)')
```

**Test 1 - Health Check:**
```bash
curl $SERVICE_URL/health
```
- [ ] Risposta 200 OK
- [ ] `"status": "healthy"`

**Test 2 - Chat Service Health:**
```bash
curl $SERVICE_URL/api/chat/health
```
- [ ] Tutti i servizi healthy

**Test 3 - Streaming:**
```bash
curl -N -X POST $SERVICE_URL/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Ciao","stream":true,"use_rag":false}'
```
- [ ] Streaming funziona
- [ ] Spazi preservati
- [ ] Tempo <5s

**Test 4 - RAG:**
```bash
curl -N -X POST $SERVICE_URL/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Parlami dei progetti","stream":true,"use_rag":true}'
```
- [ ] RAG recupera documenti
- [ ] Risposta contestuale
- [ ] Tempo <8s

---

## 5. FRONTEND INTEGRATION

### A. Test da Frontend
- [ ] Frontend può raggiungere il backend
- [ ] CORS funziona (no errori browser)
- [ ] Streaming visibile in tempo reale
- [ ] Spazi tra parole corretti
- [ ] UI responsive durante streaming

### B. Test Cases
1. **Prima domanda (nuova sessione):**
   - [ ] Genera session_id
   - [ ] Risposta corretta
   - [ ] Streaming fluido

2. **Domanda successiva (stessa sessione):**
   - [ ] Usa stesso session_id
   - [ ] History funziona
   - [ ] Risposta contestuale

3. **Domanda con RAG:**
   - [ ] Recupera documenti
   - [ ] Risposta informata
   - [ ] Sources (se richieste)

4. **Errori:**
   - [ ] Input vuoto gestito
   - [ ] Input troppo lungo gestito
   - [ ] Errore OpenAI gestito gracefully
   - [ ] Timeout gestito

---

## 6. MONITORING

### A. Logs
- [ ] Logs visibili: `gcloud run logs read vanda-chatbot --region europe-west1`
- [ ] Nessun errore critico nei log
- [ ] Metriche ragionevoli:
  ```
  INFO - Chat request - session: ..., stream: True
  INFO - Found X relevant documents
  INFO - Streaming completed - Chunks: 45, Time: 3200ms
  ```

### B. Metriche Cloud Run
- [ ] CPU usage <80%
- [ ] Memory usage <80%
- [ ] Request latency p50 <2s
- [ ] Request latency p99 <8s
- [ ] Error rate <1%

### C. Performance
- [ ] First Token Time (TTFT) <2s
- [ ] Total Response Time <5s (streaming)
- [ ] RAG Query Time <1s
- [ ] Database Query Time <500ms

---

## 7. ROLLBACK PLAN

### In caso di problemi:

**Opzione A - Rollback immediato:**
```bash
gcloud run services update-traffic vanda-chatbot \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region europe-west1
```

**Opzione B - Disable service:**
```bash
gcloud run services update vanda-chatbot \
  --no-allow-unauthenticated \
  --region europe-west1
```

**Opzione C - Redeploy versione precedente:**
```bash
git checkout PREVIOUS_COMMIT
gcloud run deploy vanda-chatbot --source .
```

---

## 8. POST-DEPLOY

### A. Documentation
- [ ] Aggiornato `CHANGELOG.md` con versione
- [ ] Aggiornato `README.md` se necessario
- [ ] Tag git creato: `git tag v1.0.1`

### B. Communication
- [ ] Team notificato del deploy
- [ ] Frontend team informato (se breaking changes)
- [ ] URL production condiviso

### C. Monitoring Setup
- [ ] Alert configurati per errori
- [ ] Dashboard metriche verificato
- [ ] Log forwarding attivo (se usato)

---

## SIGN-OFF

- [ ] **Tutti i check sono ✅**
- [ ] **Test locali passati**
- [ ] **Test production passati**
- [ ] **Performance verificate**
- [ ] **Nessun errore nei log**

**Deploy approvato da:** ___________
**Data:** ___________
**Firma:** ___________

---

## NOTES

_Aggiungi qui eventuali note specifiche del deploy:_

```
[Spazio per note]
```

---

**IMPORTANTE:** Non deployare se anche solo un check fallisce!
