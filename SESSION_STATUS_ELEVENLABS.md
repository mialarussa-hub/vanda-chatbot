# 📍 Session Status - ElevenLabs Integration & Voice Optimization

**Data**: 2025-11-08
**Ultimo aggiornamento**: Fine sessione
**Prossima sessione**: Diagnostica Safari/iOS compatibility

---

## 🎉 COMPLETATO OGGI

### ✅ **1. Integrazione ElevenLabs TTS**

Sostituito completamente OpenAI TTS con ElevenLabs per qualità audio superiore.

**Files modificati**:
- `app/config.py` - Configurazione ElevenLabs
- `app/api/voice.py` - Endpoint TTS con ElevenLabs API
- `requirements.txt` - Aggiunto requests==2.31.0
- `cloudbuild.yaml` - Secret elevenlabs-api-key
- `.env.example` - Documentato ELEVENLABS_API_KEY

**Configurazione**:
- Voice ID: `QITiGyM4owEZrBEf0QV8` (voce italiana Creator plan)
- Model: `eleven_turbo_v2_5` (ottimizzato per bassa latency)
- API Key: Configurata come secret su Google Cloud

**Status**: ✅ DEPLOYED e FUNZIONANTE in produzione

---

### ✅ **2. Fix Bug Chunking TTS (3 iterazioni)**

**Problema iniziale**: Il bot ripeteva continuamente le stesse frasi dall'inizio.

**Fix #1 - Chunking base** (commit `7d472a5`):
- Aggiunto `sentTextLength` tracker
- Creato `extractCompleteSentence()` per estrarre solo frasi nuove
- Problema: Ancora duplicati

**Fix #2 - Race condition** (commit `550601b`):
- Spostato update di `sentTextLength` PRIMA di chiamata async
- Eliminata race condition con chunk rapidi
- Problema: Chunking "a cazzo" con spezzature a metà frase

**Fix #3 - Solo frasi complete** (commit `f9d0a4c`):
- Rimossa logica word-count (15+ parole)
- Ora invia SOLO frasi complete con delimitatori (. ! ?)
- Timeout 2s per testo residuo
- Risultato: ✅ **Funziona perfettamente**

---

### ✅ **3. Pulizia URL e Immagini per TTS** (commit `fecdd01`)

**Problema**: ElevenLabs leggeva URL brutti tipo "attpis due punti slash slash..."

**Soluzione**:
Creata funzione `cleanTextForTTS()` che preprocessa il testo prima di TTS:

**Sostituzioni**:
1. `![alt](url)` → "Ti mostro un'immagine rappresentativa"
2. Multiple images → "Ti mostro alcune immagini"
3. `[text](url)` → "text, ti fornisco il link per visionare la pagina"
4. `https://...` → "ti fornisco il link per visionare la pagina"

**Importante**: Chat visiva rimane invariata con link e immagini cliccabili!

**Status**: ✅ DEPLOYED e FUNZIONANTE

---

## ⚠️ PROBLEMA EMERSO - Safari/iOS Compatibility

### **Segnalazione Utente**:
> "Dall'iPhone (Safari) il riconoscimento vocale fa cagare e quando il bot risponde non si sente"

### **Analisi Preliminare**:

**Safari macOS (Desktop)**:
- ✅ `webkitSpeechRecognition` supportato (parzialmente)
- ✅ Audio playback dovrebbe funzionare
- ⚠️ Supporto buggy e meno accurato di Chrome

**Safari iOS (iPhone/iPad)**:
- ❌ `webkitSpeechRecognition` NON disponibile
- ❌ `SpeechRecognition` NON disponibile
- ❌ Audio autoplay bloccato da policy iOS
- ❌ Voice mode completamente non funzionante

### **Soluzioni Proposte**:

**Opzione A: Disabilita Voice su Safari iOS** (VELOCE)
- Detect browser/OS
- Nascondi/disabilita voice button
- Mostra messaggio: "Voice mode disponibile solo su Chrome"
- Pro: Quick win, implementazione semplice
- Contro: Funzionalità non disponibile su iOS

**Opzione B: Fix Audio Playback** (MEDIO)
- Prime audio element durante user interaction
- Riusa stesso elemento audio
- Pro: Risolve playback su Safari desktop
- Contro: STT rimane non funzionante su iOS

**Opzione C: Servizio STT Backend** (COMPLESSO)
- Integra Google Cloud Speech-to-Text o Azure
- Cattura audio con MediaRecorder
- Invia al backend per trascrizione
- Pro: Funziona su tutti i browser
- Contro: Costi aggiuntivi, latency maggiore

### **Raccomandazione**:
**Prima diagnostica, poi fix**:
1. Aggiungere logging dettagliato browser/OS capabilities
2. Testare su Safari macOS e Safari iOS
3. In base ai risultati, implementare soluzione appropriata

---

## 🚀 PROSSIMI PASSI (Prossima Sessione)

### **Priorità ALTA - Safari Compatibility**

**Step 1: Diagnostica**
```javascript
// Aggiungere in voice.js init():
- Log browser name/version
- Log OS (macOS/iOS/Windows)
- Check SpeechRecognition availability
- Check webkitSpeechRecognition availability
- Check Audio playback capabilities
- Mostrare report in console
```

**Step 2: Test su Dispositivi Reali**
- Testare su Safari macOS
- Testare su Safari iOS (iPhone)
- Raccogliere log di diagnostica

**Step 3: Implementare Fix**
In base ai risultati:
- Se Safari macOS funziona → Disabilita solo su iOS
- Se Safari macOS non funziona → Disabilita su tutti Safari
- Mostrare messaggi informativi all'utente

**File da modificare**:
- `public/js/voice.js` - Detection e diagnostica
- `public/js/app.js` - UI conditionale per voice button
- Eventuale messaggio/tooltip per utenti Safari

---

## 📊 STATO DEPLOYMENT

### **Production (Google Cloud Run)**
- URL: `https://vanda-chatbot-ddslq3mmyq-ew.a.run.app`
- Revision: `vanda-chatbot-00030-x7q` (o più recente)
- Status: ✅ HEALTHY
- Last Deploy: 2025-11-08

### **Endpoints Disponibili**
- `POST /api/chat` - Chat con streaming SSE
- `POST /api/voice/tts-chunk` - TTS con ElevenLabs
- `GET /api/voice/health` - Health check TTS

### **Secrets Configurati**
- `openai-key` - OpenAI API (per LLM)
- `supabase-url` - Supabase URL
- `supabase-key` - Supabase anon key
- `elevenlabs-api-key` - ElevenLabs API (TTS) ✅ NEW

---

## 📁 FILES CHIAVE

### **Backend**
- `app/api/voice.py` - Endpoint TTS ElevenLabs (183 lines)
- `app/config.py` - Settings (voice_id, model_id)
- `app/api/chat.py` - Chat endpoint con streaming
- `cloudbuild.yaml` - CI/CD config

### **Frontend**
- `public/js/voice.js` - VoiceManager (STT + TTS) ⭐ MODIFICATO OGGI
- `public/js/app.js` - Main app logic
- `public/js/config.js` - API URL config
- `index.html` - Voice UI

### **Docs**
- `CLAUDE_RULES.md` - Regole sviluppo (SEMPRE chiedere permesso!)
- `SESSION_STATUS.md` - Status generale progetto
- `SESSION_STATUS_ELEVENLABS.md` - Questo file ⭐

---

## 🎯 COMMIT HISTORY (Oggi)

```
fecdd01 - feat: Clean URLs and images from text before TTS generation
f9d0a4c - feat: Optimize TTS chunking to send only complete sentences
550601b - fix: Resolve race condition causing duplicate TTS requests
0587ccf - fix: Resolve TTS chunking bug causing repeated audio playback
2b8e77f - chore: Trigger rebuild after fixing secret permissions
7d472a5 - feat: Replace OpenAI TTS with ElevenLabs for superior voice quality
```

---

## 💰 COSTI STIMATI

### **ElevenLabs Creator Plan**
- Piano: $22/mese
- Crediti: 100,000 caratteri/mese
- Consumo stimato: ~50-70k caratteri/mese (uso normale)
- Buffer: Abbastanza margine

### **Nota Importante**:
ElevenLabs costa ~13x più di OpenAI TTS, ma la qualità è significativamente superiore.
Piano Creator dovrebbe essere sufficiente per il traffico attuale.

---

## ✅ QUALITÀ VOICE ATTUALE

### **Funziona Perfettamente Su**:
- ✅ Chrome Desktop (Windows/Mac/Linux)
- ✅ Chrome Mobile (Android)
- ✅ Edge Desktop
- ⚠️ Safari macOS (da verificare)

### **NON Funziona Su**:
- ❌ Safari iOS (confermato)
- ❌ Firefox (Web Speech API non supportata)

### **Qualità Audio**:
- ✅ Voce italiana naturale ed espressiva
- ✅ Intonazione corretta (frasi complete)
- ✅ Nessuna ripetizione (bug risolti)
- ✅ URL puliti (non legge link brutti)
- ✅ Latency ~2-3 secondi

---

## 🧪 COME TESTARE (Prossima Sessione)

### **Test 1: Safari macOS**
1. Apri chatbot su Safari (Mac)
2. Apri DevTools Console
3. Attiva voice mode
4. Verifica log diagnostici
5. Testa STT (parla)
6. Testa TTS (ascolta risposta)

### **Test 2: Safari iOS**
1. Apri chatbot su iPhone (Safari)
2. Apri Remote DevTools (via Mac)
3. Attiva voice mode
4. Verifica log diagnostici
5. Documenta errori

### **Test 3: Chrome Mobile (controllo)**
1. Stesso test su Chrome Android
2. Verifica che funzioni correttamente
3. Baseline per confronto

---

## 📝 NOTE TECNICHE

### **Web Speech API - Browser Support**

**Speech Recognition (STT)**:
```
Chrome Desktop:   ✅ SpeechRecognition
Chrome Android:   ✅ webkitSpeechRecognition
Edge Desktop:     ✅ SpeechRecognition
Safari macOS:     ⚠️ webkitSpeechRecognition (buggy)
Safari iOS:       ❌ NON SUPPORTATO
Firefox:          ❌ NON SUPPORTATO
```

**Audio Playback (TTS)**:
```
Chrome:   ✅ Nessun problema
Edge:     ✅ Nessun problema
Safari:   ⚠️ Autoplay restrictions
iOS:      ❌ Severe autoplay restrictions
```

### **Workaround Possibili per iOS**:

1. **Audio Priming**:
```javascript
// Durante click su voice button:
const audio = new Audio();
audio.play().then(() => {
    // Audio "primed", ora autoplay dovrebbe funzionare
});
```

2. **Elemento Audio Persistente**:
```javascript
// Crea <audio> nel DOM, riusalo
<audio id="tts-audio"></audio>
// Cambia solo src, non ricreare elemento
```

3. **MediaSource API**:
```javascript
// Usa MediaSource invece di Blob URL
// Più compatibile con Safari
```

---

## 🎤 VOICE.JS - Configurazione Attuale

```javascript
config: {
    voice: 'nova',                  // Legacy (non usato con ElevenLabs)
    model: 'tts-1',                 // Legacy (non usato con ElevenLabs)
    speed: 1.0,                     // Usato da ElevenLabs
    silenceTimeout: 1500,           // STT silence detection
    minChunkWords: 15,              // NON più usato (solo delimitatori)
    chunkTimeoutMs: 2000            // Timeout per testo residuo
}
```

**Note**:
- `minChunkWords` non è più utilizzato dopo l'ottimizzazione
- Chunking ora basato SOLO su delimitatori (. ! ?)
- Timeout 2s invia testo residuo alla fine dello streaming

---

## 🔗 RISORSE UTILI

### **Documentazione**
- [ElevenLabs API Docs](https://elevenlabs.io/docs)
- [Web Speech API MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
- [Safari Audio Autoplay Policy](https://webkit.org/blog/7734/auto-play-policy-changes-for-macos/)

### **Browser Compatibility**
- [Can I Use - Speech Recognition](https://caniuse.com/speech-recognition)
- [Can I Use - Audio Autoplay](https://caniuse.com/audio-api)

---

## ⚠️ REMINDER IMPORTANTE

### **REGOLE DI SVILUPPO** (da CLAUDE_RULES.md):

**PRIMA di modificare qualsiasi file**:
1. ❌ FERMARSI
2. 📝 Spiegare COSA vuoi modificare (file, linee, codice)
3. 💡 Spiegare PERCHÉ (problema da risolvere)
4. ⏸️ ATTENDERE consenso esplicito ("procedi", "ok", "vai")
5. ✅ SOLO DOPO procedere

**Workflow obbligatorio**:
```
Analizza → FERMATI → Spiega → Attendi → Procedi
```

---

## 🎯 QUICK START PROSSIMA SESSIONE

1. **Leggi questo file** (SESSION_STATUS_ELEVENLABS.md)
2. **Leggi CLAUDE_RULES.md** (regole di sviluppo)
3. **Decidi**: Quale soluzione implementare per Safari?
4. **Testa**: Safari macOS e iOS con diagnostica
5. **Implementa**: Fix basato sui risultati test

---

## 📞 COMANDI UTILI

### **Test Locale**
```bash
cd D:\PROGETTI\AGENTIKA\WEB\vanda-chatbot
"venv/Scripts/python.exe" test_elevenlabs_tts.py
```

### **Deploy**
```bash
git add .
git commit -m "message"
git push origin master
# Auto-deploy via Cloud Build
```

### **Check Deployment**
```bash
gcloud run services describe vanda-chatbot --region=europe-west1
```

### **Test Endpoint**
```bash
# Health check
curl https://vanda-chatbot-ddslq3mmyq-ew.a.run.app/api/voice/health

# TTS test
curl -X POST https://vanda-chatbot-ddslq3mmyq-ew.a.run.app/api/voice/tts-chunk \
  -H "Content-Type: application/json" \
  -d '{"text":"Test italiano"}' \
  --output test.mp3
```

---

**Buon riposo! Ci vediamo alla prossima sessione! 🎤✨**

**Status finale**: Voice integration funzionante perfettamente su Chrome, da diagnosticare/fixare Safari.
