# Quick Test Guide - Streaming SSE Ottimizzato

## Test Veloce (2 minuti)

### 1. Test Base Funzionalità
```
1. Apri: D:\PROGETTI\AGENTIKA\WEB\vanda-chatbot\public\index.html
2. F12 → Console
3. Invia: "Parlami dei vostri servizi"
4. Verifica console:
   ✅ "🔄 Starting SSE stream..."
   ✅ "⚡ First chunk received - Latency: XXXms"
   ✅ "✅ Stream completed - Chunks: XX"
```

**Risultato atteso**: Testo appare progressivamente con cursore lampeggiante `|`

---

### 2. Test Visual Feedback
```
Cosa osservare:
✅ Typing indicator (puntini) appare subito
✅ Scompare con primo token
✅ Cursore | lampeggia alla fine del testo
✅ Cursore scompare quando completo
✅ Scroll automatico segue il testo
```

---

### 3. Test Performance
```
Console deve mostrare:
⚡ Latency < 500ms        → Backend veloce ✅
📦 Δ < 100ms tra chunks   → Streaming fluido ✅
✅ Chunks > 20            → Token-by-token ✅
```

---

## Debug Mode (Se problemi)

### Attiva Log Dettagliati
```javascript
// File: public/js/config.js
DEBUG_STREAMING: true  // Cambia da false a true
```

Poi ricarica e verifica console:
```
📦 Chunk 1 (Δ23.4ms): data: Certo
📦 Chunk 2 (Δ18.2ms): data: ,
📦 Chunk 3 (Δ21.5ms): data:  posso
```

---

## Troubleshooting Veloce

### ❌ Testo appare tutto insieme
```
1. Check Network tab → /api/chat → Response
2. Dovresti vedere dati incrementali
3. Se appare tutto insieme → problema backend
```

### ❌ Cursore non visibile
```
1. Hard refresh: Ctrl + Shift + R
2. Check console errori JavaScript
3. Verifica CSS caricato: Inspect cursore
```

### ❌ Scroll jittery
```javascript
// config.js - Aumenta throttle
SCROLL_THROTTLE_MS: 100  // da 50 a 100
```

### ❌ Latenza alta (> 1 sec)
```
⚡ First chunk > 1000ms → Problema backend, non frontend
Verifica: Cold start? Rete lenta? Backend occupato?
```

---

## Test Production-Ready

Prima di deploy:
- [ ] Streaming visibile token-by-token
- [ ] Cursore lampeggia correttamente
- [ ] Scroll fluido senza lag
- [ ] Console senza errori
- [ ] Latenza < 500ms
- [ ] `DEBUG_STREAMING: false` in config

---

## Command Quick Reference

```bash
# Validate syntax
cd "D:\PROGETTI\AGENTIKA\WEB\vanda-chatbot"
node --check public/js/app.js
node --check public/js/config.js

# Serve locally (se hai http-server)
npx http-server public -p 8080
# Poi apri: http://localhost:8080
```

---

## Performance Targets

| Metrica | Target | Misurazione |
|---------|--------|-------------|
| First Chunk | < 500ms | Console `⚡` |
| Chunk Δ | < 50ms | Console `Δ` |
| FPS | 60fps | DevTools Performance |
| CPU | < 30% | Task Manager |

---

## Link Utili

- Report completo: `docs/FRONTEND_SSE_OPTIMIZATION_REPORT.md`
- Codice ottimizzato: `public/js/app.js` (riga 218-332)
- Configurazione: `public/js/config.js`
- Stili cursore: `public/css/style.css` (riga 474-496)
