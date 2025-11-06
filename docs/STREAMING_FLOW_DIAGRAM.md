# VANDA Chatbot - Streaming Flow Diagram

## 1. Flow Completo: User → Backend → Frontend

```
┌─────────────┐
│   UTENTE    │
│  (Browser)  │
└──────┬──────┘
       │ 1. Click "Invia" o Enter
       │
       ▼
┌─────────────────────────────────────────┐
│  FRONTEND (app.js)                      │
├─────────────────────────────────────────┤
│  handleSendMessage()                    │
│  ├─ Valida input                        │
│  ├─ addMessage('user', text)            │
│  ├─ showTypingIndicator()               │
│  └─ sendMessageToAPI(text)              │
└──────┬──────────────────────────────────┘
       │ 2. POST /api/chat
       │    {message, session_id, stream:true}
       │
       ▼
┌─────────────────────────────────────────┐
│  BACKEND (Python/FastAPI)               │
│  Cloud Run: europe-west1                │
├─────────────────────────────────────────┤
│  ├─ Riceve richiesta                    │
│  ├─ Query RAG (Pinecone)                │
│  ├─ Genera prompt                       │
│  └─ Stream da OpenAI GPT-4o-mini        │
│     └─ yield token by token             │
└──────┬──────────────────────────────────┘
       │ 3. SSE Stream Response
       │    data: Certo\n
       │    data: ,\n
       │    data:  posso\n
       │    ...
       │    data: [DONE]\n
       │
       ▼
┌─────────────────────────────────────────┐
│  FRONTEND - handleStreamResponse()      │
├─────────────────────────────────────────┤
│  ├─ reader.read() → chunk               │
│  ├─ decoder.decode(chunk, {stream:true})│
│  ├─ Buffer management (linee incomplete)│
│  ├─ Parse "data: ..." lines             │
│  ├─ Accumula: assistantMessage += token │
│  └─ requestAnimationFrame(() => {       │
│      └─ updateMessageContentOptimized() │
│           ├─ Update TextNode diretto    │
│           ├─ Mantieni cursore |         │
│           └─ throttledScrollToBottom()  │
│     })                                   │
└──────┬──────────────────────────────────┘
       │ 4. Visual Update (60fps)
       │
       ▼
┌─────────────────────────────────────────┐
│  DOM / UI                               │
├─────────────────────────────────────────┤
│  🤖 [Testo che cresce....|]  ← cursore  │
│                            lampeggiante  │
│  ↓ Auto-scroll fluido                   │
└─────────────────────────────────────────┘
       │ 5. Stream completo
       │    data: [DONE]
       │
       ▼
┌─────────────────────────────────────────┐
│  Cleanup                                │
├─────────────────────────────────────────┤
│  ├─ removeStreamingCursor()             │
│  ├─ hideTypingIndicator()               │
│  ├─ setLoadingState(false)              │
│  └─ console.log("Stream completed")     │
└─────────────────────────────────────────┘
```

---

## 2. Timeline Dettagliato (Esempio Reale)

```
T=0ms       User preme "Invia"
            └─ handleSendMessage()
            └─ showTypingIndicator() → 🤖 ...

T=50ms      POST /api/chat inviato
            └─ Request in volo

T=250ms     Backend riceve richiesta
            └─ Query RAG Pinecone

T=400ms     Primo token generato da GPT
            └─ Backend: yield "data: Certo\n"

T=450ms     ⚡ FRONTEND: Primo chunk ricevuto
            └─ Latency: 450ms
            └─ hideTypingIndicator()
            └─ Crea messaggio con cursore |
            └─ DOM: "Certo|"

T=470ms     Chunk 2: "data: ,\n"
            └─ Δ20ms
            └─ DOM: "Certo,|"

T=490ms     Chunk 3: "data:  posso\n"
            └─ Δ20ms
            └─ DOM: "Certo, posso|"

T=510ms     Chunk 4: "data:  aiutarti\n"
            └─ Δ20ms
            └─ DOM: "Certo, posso aiutarti|"

...         [Continua streaming]
            Δ18-25ms per chunk
            60fps rendering
            Scroll throttled ogni 50ms

T=2500ms    Ultimo chunk: "data: [DONE]\n"
            └─ Stream completo
            └─ removeStreamingCursor()
            └─ DOM: "Certo, posso aiutarti..."
            └─ console.log("✅ Stream completed")
            └─ Total: 2500ms, 45 chunks

T=2550ms    UI pronta per nuovo messaggio
            └─ setLoadingState(false)
            └─ Input ri-abilitato
```

---

## 3. Gestione Buffer (Dettaglio Tecnico)

### Problema: Chunk Incompleto

```
Chunk 1 arriva: "data: Cert"
                         ^ linea incompleta, manca \n

Chunk 2 arriva: "o, posso\ndata: aiutarti\n"
                ^ completa la linea precedente
```

### Soluzione: Buffer Management

```javascript
let buffer = '';

// Chunk 1
buffer += "data: Cert";           // buffer = "data: Cert"
lines = buffer.split('\n');       // ["data: Cert"]
buffer = lines.pop();             // buffer = "data: Cert", lines = []
// Nessuna linea completa → skip processamento

// Chunk 2
buffer += "o, posso\ndata: aiutarti\n";  // buffer = "data: Certo, posso\ndata: aiutarti\n"
lines = buffer.split('\n');              // ["data: Certo, posso", "data: aiutarti", ""]
buffer = lines.pop();                    // buffer = "", lines = ["data: Certo, posso", "data: aiutarti"]

// Processa linee complete
for (line of lines) {
    // "data: Certo, posso" → token: "Certo, posso" ✅
    // "data: aiutarti"     → token: "aiutarti" ✅
}
```

**Risultato**: Nessun token perso, nessun parsing errato ✅

---

## 4. Rendering Optimization

### ❌ PRIMA: Update Diretto (Problematico)

```javascript
for each chunk:
    assistantMessage += token
    contentDiv.textContent = assistantMessage  ← DOM update
    scrollToBottom()                           ← Reflow
    // 100+ reflow per stream = LAG
```

**Flow**:
```
Token 1 → DOM Update → Reflow → Scroll → Reflow
Token 2 → DOM Update → Reflow → Scroll → Reflow
Token 3 → DOM Update → Reflow → Scroll → Reflow
...
100+ tokens → 100+ reflow → CPU 60% → 30fps
```

---

### ✅ DOPO: requestAnimationFrame (Ottimizzato)

```javascript
for each chunk:
    assistantMessage += token
    requestAnimationFrame(() => {          ← Schedula per next frame
        updateMessageContentOptimized()    ← Update TextNode
        throttledScrollToBottom()          ← Max 1 ogni 50ms
    })
```

**Flow**:
```
Token 1,2,3,4,5 → Accumula in buffer
                ↓
        requestAnimationFrame (16.67ms)
                ↓
        Batch update → 1 Reflow → Scroll (throttled)
                ↓
Token 6,7,8,9,10 → Accumula
                ↓
        requestAnimationFrame (16.67ms)
                ↓
        Batch update → 1 Reflow → Scroll (skip, throttled)
...
100 tokens → ~20 reflow → CPU 20% → 60fps
```

**Beneficio**: -80% reflow, rendering sincronizzato con refresh rate

---

## 5. Cursore Streaming Lifecycle

```
┌─────────────────────────────────────────┐
│  Messaggio Assistant                    │
│  ┌─────────────────────────────────┐    │
│  │  [Testo che cresce]|            │    │
│  │                     ^            │    │
│  │                     │            │    │
│  │              .streaming-cursor   │    │
│  │              - width: 2px        │    │
│  │              - blink animation   │    │
│  │              - sempre alla fine  │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘

Lifecycle:
1. addMessage(..., isStreaming=true)
   └─ <span class="streaming-cursor"></span> creato

2. updateMessageContentOptimized()
   ├─ Trova cursor esistente
   ├─ Update TextNode PRIMA del cursore
   └─ Cursore rimane alla fine (persistente)

3. Stream completo: [DONE]
   └─ removeStreamingCursor()
      └─ cursor.remove()

DOM Structure:
<div class="message-content">
  [TextNode: "Certo, posso aiutarti"]
  <span class="streaming-cursor"></span>  ← Blink animation
</div>
```

---

## 6. Scroll Throttling

### ❌ PRIMA: Scroll ad Ogni Chunk

```
Chunk 1  → scrollToBottom() → setTimeout(100ms)
Chunk 2  → scrollToBottom() → setTimeout(100ms)
Chunk 3  → scrollToBottom() → setTimeout(100ms)
...
Chunk 100 → scrollToBottom() → setTimeout(100ms)

Result: 100+ scroll events → Jittery scroll
```

---

### ✅ DOPO: Throttled (Max 1 ogni 50ms)

```javascript
let scrollThrottleTimer = null;

throttledScrollToBottom() {
    if (scrollThrottleTimer) return;  // Skip se già schedulato

    scrollThrottleTimer = setTimeout(() => {
        scroll();                     // Esegui scroll
        scrollThrottleTimer = null;   // Reset
    }, 50);
}
```

**Flow**:
```
T=0ms:   Chunk 1 → throttledScroll() → Schedula scroll per T=50ms
T=10ms:  Chunk 2 → throttledScroll() → Skip (già schedulato)
T=20ms:  Chunk 3 → throttledScroll() → Skip
T=30ms:  Chunk 4 → throttledScroll() → Skip
T=50ms:  → Esegui scroll ✅
T=60ms:  Chunk 5 → throttledScroll() → Schedula scroll per T=110ms
T=70ms:  Chunk 6 → throttledScroll() → Skip
...

Result: ~20 scroll events invece di 100+ → Smooth scroll
```

---

## 7. Performance Monitoring Flow

```javascript
// Initialization
const startTime = performance.now();
let firstChunkTime = null;
let lastChunkTime = startTime;

console.log('🔄 Starting SSE stream...');

while (streaming) {
    chunk = await reader.read();

    // First chunk latency
    if (firstChunkTime === null) {
        firstChunkTime = performance.now();
        latency = firstChunkTime - startTime;
        console.log(`⚡ First chunk - Latency: ${latency}ms`);
    }

    // Chunk interval
    now = performance.now();
    interval = now - lastChunkTime;
    lastChunkTime = now;

    if (DEBUG_STREAMING) {
        console.log(`📦 Chunk ${count} (Δ${interval}ms): ${chunk}`);
    }
}

// Completion
totalTime = performance.now() - startTime;
console.log(`✅ Stream completed - Chunks: ${count}, Duration: ${totalTime}ms`);
```

**Output Example**:
```
🔄 Starting SSE stream...
⚡ First chunk received - Latency: 234.50ms
📦 Chunk 1 (Δ23.4ms): data: Certo
📦 Chunk 2 (Δ18.2ms): data: ,
📦 Chunk 3 (Δ21.5ms): data:  posso
...
✅ Stream completed - Chunks: 45, Duration: 2341.20ms
```

**Metrics**:
- **Latency**: Backend response time
- **Δ (Delta)**: Streaming speed/consistency
- **Chunks**: Token count
- **Duration**: Total stream time

---

## 8. Error Handling Flow

```
┌─────────────────────────────────────┐
│  try {                              │
│    while (streaming) {              │
│      chunk = await reader.read()   │
│                                     │
│      if (chunk.includes('[ERROR]')) │
│         └─→ Error Handler           │
│      if (chunk.includes('[DONE]'))  │
│         └─→ Success Handler         │
│                                     │
│      processChunk(chunk)            │
│    }                                │
│  }                                  │
└────────┬────────────────────────────┘
         │
         │ catch (error)
         ▼
┌─────────────────────────────────────┐
│  Error Handler                      │
├─────────────────────────────────────┤
│  1. console.error('Stream error')   │
│  2. removeStreamingCursor()         │
│  3. hideTypingIndicator()           │
│  4. showError(message)              │
│  5. setLoadingState(false)          │
│  6. throw error (re-throw)          │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  UI Cleanup                         │
├─────────────────────────────────────┤
│  ✅ Cursore rimosso                 │
│  ✅ Typing indicator nascosto       │
│  ✅ Input ri-abilitato              │
│  ✅ Messaggio errore visibile       │
│  ✅ UI torna allo stato normale     │
└─────────────────────────────────────┘
```

---

## 9. State Management

```
┌──────────────────────────────────────────────┐
│  AppState                                    │
├──────────────────────────────────────────────┤
│  sessionId: "uuid-xxxx-xxxx"                 │
│  messages: []                                │
│  isLoading: false  ←───┐                     │
│  messageCount: 0       │                     │
└────────────────────────┼─────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
    isLoading = true              isLoading = false
        │                                 │
        ▼                                 ▼
┌───────────────────┐           ┌──────────────────┐
│  Durante Stream   │           │  Stream Completo │
├───────────────────┤           ├──────────────────┤
│ • Input disabled  │           │ • Input enabled  │
│ • Send btn: ⏳    │           │ • Send btn: 📤   │
│ • Typing...       │           │ • Ready          │
└───────────────────┘           └──────────────────┘
```

---

## 10. Complete Message Lifecycle

```
User Input
    ↓
┌───────────────────────────────────────┐
│ 1. PRE-SEND                           │
├───────────────────────────────────────┤
│ • Validate input                      │
│ • removeWelcomeScreen()               │
│ • addMessage('user', text)            │
│ • userInput.value = ''                │
│ • setLoadingState(true)               │
└───────┬───────────────────────────────┘
        │
        ↓
┌───────────────────────────────────────┐
│ 2. WAITING                            │
├───────────────────────────────────────┤
│ • showTypingIndicator()               │
│ • Display: 🤖 [... ... ...]          │
└───────┬───────────────────────────────┘
        │
        ↓ First chunk arrives
┌───────────────────────────────────────┐
│ 3. STREAMING                          │
├───────────────────────────────────────┤
│ • hideTypingIndicator()               │
│ • addMessage('assistant', '', true)   │
│ • Display: 🤖 [Text...|]  ← cursore  │
│ • Update per ogni chunk               │
│ • Scroll segue il testo               │
└───────┬───────────────────────────────┘
        │
        ↓ [DONE] arrives
┌───────────────────────────────────────┐
│ 4. COMPLETE                           │
├───────────────────────────────────────┤
│ • removeStreamingCursor()             │
│ • Display: 🤖 [Complete text]        │
│ • setLoadingState(false)              │
│ • Re-enable input                     │
└───────────────────────────────────────┘
        │
        ↓
    Ready for next message
```

---

## Visual Summary

```
┌─────────────────────────────────────────────────────────┐
│  VANDA Chatbot - Streaming Architecture                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Frontend (Browser)              Backend (Cloud Run)    │
│  ┌──────────────┐                ┌──────────────┐      │
│  │   User UI    │───Request────→ │  FastAPI     │      │
│  │              │                 │              │      │
│  │  • Input     │                 │ • RAG Query  │      │
│  │  • Messages  │                 │ • GPT Stream │      │
│  │  • Typing... │                 │ • Token/Token│      │
│  │              │                 │              │      │
│  │              │←───SSE Stream─── │              │      │
│  └──────┬───────┘   data: token   └──────────────┘      │
│         │           data: token                         │
│         │           data: [DONE]                        │
│         ▼                                               │
│  ┌──────────────────────────────────┐                  │
│  │  handleStreamResponse()          │                  │
│  │  ├─ Buffer management            │                  │
│  │  ├─ Parse SSE lines              │                  │
│  │  └─ requestAnimationFrame        │                  │
│  │      └─ Update DOM (60fps)       │                  │
│  │         ├─ TextNode direct       │                  │
│  │         ├─ Streaming cursor |    │                  │
│  │         └─ Throttled scroll      │                  │
│  └──────────────────────────────────┘                  │
│                                                         │
│  Performance:                                           │
│  ⚡ Latency: < 500ms                                    │
│  🎯 FPS: 60fps                                          │
│  💻 CPU: < 30%                                          │
│  ✨ UX: Smooth & Clear                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

**Documento**: Flow Diagram Streaming SSE
**Versione**: 1.0
**Data**: 2025-11-05
