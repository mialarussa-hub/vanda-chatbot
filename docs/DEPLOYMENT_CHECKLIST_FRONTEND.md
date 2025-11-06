# Frontend Streaming - Deployment Checklist

## Pre-Deployment Verification

### 1. Configurazione Corretta

```javascript
// File: public/js/config.js

// ✅ Verifica questi valori prima del deploy
DEBUG_STREAMING: false,          // DEVE essere false in produzione
SCROLL_THROTTLE_MS: 50,          // OK per produzione (50-100ms)
DEFAULT_REQUEST: {
    stream: true,                 // DEVE essere true
    use_rag: true,
    include_sources: false
}
```

**Check**:
- [ ] `DEBUG_STREAMING: false` (niente log verbosi in prod)
- [ ] `stream: true` (abilita streaming)
- [ ] `SCROLL_THROTTLE_MS` tra 50-100ms

---

### 2. File Modificati

Verifica che questi file contengano le ottimizzazioni:

**JavaScript**:
- [ ] `public/js/app.js` - Funzione `handleStreamResponse()` ottimizzata (riga ~218)
- [ ] `public/js/app.js` - Funzione `updateMessageContentOptimized()` presente (riga ~450)
- [ ] `public/js/app.js` - Funzione `throttledScrollToBottom()` presente (riga ~554)
- [ ] `public/js/config.js` - Parametri `DEBUG_STREAMING` e `SCROLL_THROTTLE_MS` presenti

**CSS**:
- [ ] `public/css/style.css` - Classe `.streaming-cursor` presente (riga ~474)
- [ ] `public/css/style.css` - Animazione `@keyframes blink` presente (riga ~489)

**HTML**:
- [ ] `public/index.html` - Include `config.js` prima di `app.js`

---

### 3. Test Funzionali

#### Test Base
```bash
# 1. Apri applicazione
# 2. F12 → Console
# 3. Invia messaggio
# 4. Verifica console output
```

**Output atteso**:
```
🔄 Starting SSE stream...
⚡ First chunk received - Latency: XXXms
✅ Stream completed - Chunks: XX, Duration: XXXXms
```

**Visual checks**:
- [ ] Typing indicator appare prima dello streaming
- [ ] Typing indicator scompare con primo token
- [ ] Testo appare progressivamente (non tutto insieme)
- [ ] Cursore `|` lampeggia alla fine del testo
- [ ] Cursore scompare quando messaggio completo
- [ ] Scroll automatico segue il testo fluidamente

---

### 4. Performance Tests

#### Browser DevTools Performance
```
1. DevTools → Performance
2. Click Record
3. Invia messaggio lungo
4. Stop recording
5. Analizza
```

**Targets**:
- [ ] FPS >= 55fps (ideale: 60fps)
- [ ] Main thread non bloccato per > 50ms
- [ ] Nessun "Long Task" (> 50ms)

#### CPU Usage
```
1. Task Manager
2. Invia messaggio lungo
3. Monitor CPU durante streaming
```

**Target**:
- [ ] CPU < 30% durante streaming

---

### 5. Network Tests

#### DevTools Network Tab
```
1. DevTools → Network
2. Invia messaggio
3. Click su /api/chat
4. Tab "Response"
```

**Verifica**:
- [ ] I chunk SSE appaiono progressivamente
- [ ] Formato: `data: [contenuto]`
- [ ] Non tutto il contenuto arriva in un colpo solo
- [ ] Stream termina con `data: [DONE]`

#### Throttling Test
```
DevTools → Network → Throttling → Fast 3G
```

**Verifica**:
- [ ] Streaming ancora fluido (anche se più lento)
- [ ] Nessun freeze dell'UI
- [ ] Cursore lampeggia correttamente

---

### 6. Browser Compatibility

Test su questi browser:

**Desktop**:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Edge (latest)
- [ ] Safari (se disponibile)

**Mobile** (DevTools device emulation):
- [ ] iPhone (Safari)
- [ ] Android (Chrome)

**Verifiche per ogni browser**:
- Streaming visibile
- Cursore animato
- Scroll fluido
- Nessun errore console

---

### 7. Error Handling

#### Test Offline
```
1. DevTools → Network → Offline
2. Invia messaggio
```

**Verifica**:
- [ ] Messaggio errore appare
- [ ] Cursore streaming rimosso
- [ ] UI torna allo stato normale
- [ ] Console log errore

#### Test Timeout
```
1. Backend lento/non risponde
2. Invia messaggio
3. Attendi timeout
```

**Verifica**:
- [ ] Gestione timeout corretta
- [ ] UI non bloccata
- [ ] Errore mostrato all'utente

---

### 8. Regression Tests

Verifica che funzionalità esistenti non siano rotte:

**Chat Base**:
- [ ] Invio messaggio funziona
- [ ] Messaggi utente appaiono correttamente
- [ ] Storia conversazione preservata
- [ ] Session ID mantenuto

**UI Controls**:
- [ ] Bottone Clear funziona
- [ ] Bottone Fullscreen funziona
- [ ] Suggestion buttons funzionano
- [ ] Quick actions funzionano

**Input**:
- [ ] Input disabilitato durante caricamento
- [ ] Enter invia messaggio
- [ ] Validazione lunghezza messaggio
- [ ] Focus automatico dopo invio

---

### 9. Code Quality

#### Syntax Check
```bash
cd D:\PROGETTI\AGENTIKA\WEB\vanda-chatbot
node --check public/js/app.js
node --check public/js/config.js
```

**Output atteso**: Nessun errore

#### Console Errors
```
1. F12 → Console
2. Filtra "Errors"
3. Usa applicazione per 5 minuti
```

**Verifica**:
- [ ] Nessun errore JavaScript
- [ ] Nessun warning critico
- [ ] Nessun 404 per risorse

---

### 10. Production Settings

#### Final Config Review
```javascript
// public/js/config.js - PRODUCTION VALUES

const CONFIG = {
    API_URL: 'https://vanda-chatbot-515064966632.europe-west1.run.app',  // ✅
    DEBUG_STREAMING: false,           // ✅ MUST be false
    SCROLL_THROTTLE_MS: 50,           // ✅ OK
    DEFAULT_REQUEST: {
        stream: true,                  // ✅ MUST be true
        use_rag: true,
        include_sources: false
    }
};
```

**Checklist**:
- [ ] `API_URL` punta a produzione
- [ ] `DEBUG_STREAMING` è `false`
- [ ] `stream` è `true`
- [ ] Nessun console.log custom aggiunto

---

### 11. Documentation

Verifica che la documentazione sia completa:

- [ ] `FRONTEND_SSE_OPTIMIZATION_REPORT.md` - Report completo
- [ ] `QUICK_TEST_STREAMING.md` - Guida test veloce
- [ ] `CODE_COMPARISON.md` - Confronto prima/dopo
- [ ] `DEPLOYMENT_CHECKLIST_FRONTEND.md` - Questa checklist

---

### 12. Rollback Plan

Prima del deploy, prepara rollback:

**Backup files**:
```bash
# Crea backup pre-ottimizzazione
cp public/js/app.js public/js/app.js.pre-streaming-optimization
cp public/js/config.js public/js/config.js.pre-streaming-optimization
cp public/css/style.css public/css/style.css.pre-streaming-optimization
```

**Rollback procedure**:
```bash
# Se problemi, ripristina backup
cp public/js/app.js.pre-streaming-optimization public/js/app.js
cp public/js/config.js.pre-streaming-optimization public/js/config.js
cp public/css/style.css.pre-streaming-optimization public/css/style.css
```

- [ ] Backup creato
- [ ] Procedura rollback testata

---

## Post-Deployment Monitoring

### Primo Giorno

**Metriche da monitorare**:
- [ ] Nessun errore JavaScript (Analytics/Sentry)
- [ ] Tempo risposta prima chunk < 500ms
- [ ] Nessun report utenti di malfunzionamenti
- [ ] Streaming visibile su tutti i browser

### Prima Settimana

**Raccolta feedback**:
- [ ] Utenti percepiscono streaming più fluido?
- [ ] Nessun problema di performance segnalato?
- [ ] Metriche RUM (Real User Monitoring) positive?

---

## Quick Fix Reference

### Se streaming non visibile

1. **Check console**:
   ```javascript
   // Temporarily enable debug
   CONFIG.DEBUG_STREAMING = true
   ```

2. **Check Network**:
   - Response deve essere incrementale
   - Se tutto in una volta → problema backend/proxy

3. **Check config**:
   ```javascript
   console.log(CONFIG.DEFAULT_REQUEST.stream); // MUST be true
   ```

---

### Se cursore non appare

1. **Hard refresh**: Ctrl + Shift + R
2. **Check CSS**:
   ```javascript
   console.log(getComputedStyle(document.querySelector('.streaming-cursor')));
   ```
3. **Check HTML**:
   ```javascript
   console.log(document.querySelector('.streaming-cursor')); // Should exist
   ```

---

### Se scroll jittery

```javascript
// In config.js, increase throttle
SCROLL_THROTTLE_MS: 100  // from 50
```

---

## Sign-Off

**Completato da**: _________________
**Data**: _________________
**Tutti i check passed**: [ ] SI [ ] NO
**Note**: _________________

---

## Support Contacts

**Documentazione completa**: `docs/FRONTEND_SSE_OPTIMIZATION_REPORT.md`
**Test rapidi**: `docs/QUICK_TEST_STREAMING.md`
**Confronto codice**: `docs/CODE_COMPARISON.md`

**Files modificati**:
- `public/js/app.js`
- `public/js/config.js`
- `public/css/style.css`
