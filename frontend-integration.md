# VANDA Chatbot - Integrazione Frontend

Guida completa per integrare il chatbot VANDA nel sito agentika.io

---

## 🌐 URL API

```
https://vanda-chatbot-515064966632.europe-west1.run.app
```

---

## 📋 Endpoints Disponibili

- **POST** `/api/chat` - Chat endpoint (streaming & non-streaming)
- **GET** `/health` - Health check
- **GET** `/api/chat/health` - Health check servizi
- **GET** `/api/chat/stats` - Statistiche sessioni

---

## 🎯 Opzione 1: React/Next.js Component (Streaming)

### Componente Chat Completo

```typescript
// components/VandaChatbot.tsx
import { useState, useRef, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function VandaChatbot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const API_URL = 'https://vanda-chatbot-515064966632.europe-west1.run.app';

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);

    // Aggiungi messaggio utente
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
          stream: true,
          use_rag: true,
        }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      // Leggi SSE stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';

      // Aggiungi placeholder per messaggio assistant
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.slice(6).trim();

            if (content === '[DONE]') {
              setIsLoading(false);
              return;
            }

            if (content.startsWith('[ERROR]')) {
              console.error('Error from API:', content);
              setIsLoading(false);
              return;
            }

            // Ignora [SOURCES]
            if (content.startsWith('[SOURCES]')) {
              continue;
            }

            // Aggiorna messaggio assistant in tempo reale
            assistantMessage += content;
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage.role === 'assistant') {
                lastMessage.content = assistantMessage;
              }
              return newMessages;
            });
          }
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Scusa, si è verificato un errore. Riprova.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <h3>🏠 VANDA Assistant</h3>
        <p>Chiedi informazioni sui nostri progetti</p>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <p>👋 Ciao! Come posso aiutarti?</p>
            <div className="suggestions">
              <button onClick={() => setInput('Parlami dei vostri servizi')}>
                🏡 Servizi
              </button>
              <button onClick={() => setInput('Mostramì un progetto residenziale')}>
                🛋️ Progetti
              </button>
              <button onClick={() => setInput('Quali sono i tempi di realizzazione?')}>
                ⏱️ Tempi
              </button>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? '👤' : '🤖'}
            </div>
            <div className="message-content">
              {msg.content}
            </div>
          </div>
        ))}

        {isLoading && messages[messages.length - 1]?.content === '' && (
          <div className="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Scrivi un messaggio..."
          disabled={isLoading}
        />
        <button onClick={sendMessage} disabled={isLoading || !input.trim()}>
          {isLoading ? '⏳' : '📤'}
        </button>
      </div>

      <style jsx>{`
        .chat-container {
          display: flex;
          flex-direction: column;
          height: 600px;
          max-width: 500px;
          border: 1px solid #ddd;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .chat-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px;
          text-align: center;
        }

        .chat-header h3 {
          margin: 0 0 5px 0;
          font-size: 20px;
        }

        .chat-header p {
          margin: 0;
          font-size: 14px;
          opacity: 0.9;
        }

        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          background: #f8f9fa;
        }

        .welcome-message {
          text-align: center;
          padding: 40px 20px;
        }

        .suggestions {
          display: flex;
          flex-direction: column;
          gap: 10px;
          margin-top: 20px;
        }

        .suggestions button {
          background: white;
          border: 2px solid #667eea;
          color: #667eea;
          padding: 12px 20px;
          border-radius: 8px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }

        .suggestions button:hover {
          background: #667eea;
          color: white;
          transform: translateY(-2px);
        }

        .message {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
          animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .message-user {
          flex-direction: row-reverse;
        }

        .message-avatar {
          font-size: 24px;
          flex-shrink: 0;
        }

        .message-content {
          background: white;
          padding: 12px 16px;
          border-radius: 12px;
          max-width: 70%;
          word-wrap: break-word;
        }

        .message-user .message-content {
          background: #667eea;
          color: white;
        }

        .typing-indicator {
          display: flex;
          gap: 4px;
          padding: 12px;
        }

        .typing-indicator span {
          width: 8px;
          height: 8px;
          background: #667eea;
          border-radius: 50%;
          animation: bounce 1.4s infinite ease-in-out;
        }

        .typing-indicator span:nth-child(1) {
          animation-delay: -0.32s;
        }

        .typing-indicator span:nth-child(2) {
          animation-delay: -0.16s;
        }

        @keyframes bounce {
          0%, 80%, 100% {
            transform: scale(0);
          }
          40% {
            transform: scale(1);
          }
        }

        .chat-input {
          display: flex;
          gap: 8px;
          padding: 16px;
          background: white;
          border-top: 1px solid #ddd;
        }

        .chat-input input {
          flex: 1;
          padding: 12px 16px;
          border: 1px solid #ddd;
          border-radius: 24px;
          font-size: 14px;
          outline: none;
        }

        .chat-input input:focus {
          border-color: #667eea;
        }

        .chat-input button {
          padding: 12px 20px;
          background: #667eea;
          color: white;
          border: none;
          border-radius: 24px;
          cursor: pointer;
          font-size: 16px;
          transition: background 0.2s;
        }

        .chat-input button:hover:not(:disabled) {
          background: #5568d3;
        }

        .chat-input button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
```

### Uso del Componente

```tsx
// pages/index.tsx o dove vuoi inserire il chatbot
import VandaChatbot from '@/components/VandaChatbot';

export default function Home() {
  return (
    <div>
      <h1>Benvenuto su VANDA Designers</h1>

      {/* Chat Widget */}
      <VandaChatbot />
    </div>
  );
}
```

---

## 🎯 Opzione 2: JavaScript Vanilla (Senza Framework)

```html
<!-- Aggiungi questo HTML dove vuoi il chatbot -->
<div id="vanda-chatbot"></div>

<script>
(function() {
  const API_URL = 'https://vanda-chatbot-515064966632.europe-west1.run.app';
  const sessionId = crypto.randomUUID();
  let messages = [];

  // Crea UI
  const container = document.getElementById('vanda-chatbot');
  container.innerHTML = `
    <div class="vanda-chat">
      <div class="vanda-chat-header">
        <h3>🏠 VANDA Assistant</h3>
      </div>
      <div class="vanda-chat-messages" id="vanda-messages"></div>
      <div class="vanda-chat-input">
        <input type="text" id="vanda-input" placeholder="Scrivi un messaggio..." />
        <button id="vanda-send">📤</button>
      </div>
    </div>
  `;

  const messagesDiv = document.getElementById('vanda-messages');
  const input = document.getElementById('vanda-input');
  const sendBtn = document.getElementById('vanda-send');

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    // Aggiungi messaggio utente
    messages.push({ role: 'user', content: text });
    renderMessages();
    input.value = '';

    // Chiamata API con streaming
    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          stream: true,
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';

      messages.push({ role: 'assistant', content: '' });
      renderMessages();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.slice(6).trim();
            if (content === '[DONE]') break;
            if (!content.startsWith('[')) {
              assistantMessage += content;
              messages[messages.length - 1].content = assistantMessage;
              renderMessages();
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      messages.push({ role: 'assistant', content: 'Errore di connessione.' });
      renderMessages();
    }
  }

  function renderMessages() {
    messagesDiv.innerHTML = messages
      .map(
        (msg) => `
      <div class="vanda-message vanda-message-${msg.role}">
        <div class="vanda-avatar">${msg.role === 'user' ? '👤' : '🤖'}</div>
        <div class="vanda-content">${msg.content}</div>
      </div>
    `
      )
      .join('');
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  sendBtn.onclick = sendMessage;
  input.onkeypress = (e) => e.key === 'Enter' && sendMessage();
})();
</script>

<style>
.vanda-chat {
  max-width: 400px;
  height: 500px;
  border: 1px solid #ddd;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  font-family: Arial, sans-serif;
}
.vanda-chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px;
  text-align: center;
}
.vanda-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f8f9fa;
}
.vanda-message {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.vanda-message-user {
  flex-direction: row-reverse;
}
.vanda-avatar {
  font-size: 20px;
}
.vanda-content {
  background: white;
  padding: 10px 14px;
  border-radius: 12px;
  max-width: 70%;
}
.vanda-message-user .vanda-content {
  background: #667eea;
  color: white;
}
.vanda-chat-input {
  display: flex;
  gap: 8px;
  padding: 12px;
  background: white;
  border-top: 1px solid #ddd;
}
.vanda-chat-input input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 20px;
  outline: none;
}
.vanda-chat-input button {
  padding: 10px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
}
</style>
```

---

## 🎯 Opzione 3: Chat Widget Floating (Pop-up)

Per un widget che si apre in basso a destra:

```html
<!-- Aggiungi questo prima di </body> -->
<div id="vanda-widget">
  <button id="vanda-toggle" class="vanda-fab">💬</button>
  <div id="vanda-window" class="vanda-window" style="display: none;">
    <!-- Inserisci qui il chatbot component -->
  </div>
</div>

<script>
document.getElementById('vanda-toggle').onclick = function() {
  const window = document.getElementById('vanda-window');
  window.style.display = window.style.display === 'none' ? 'flex' : 'none';
};
</script>

<style>
.vanda-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  font-size: 28px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 1000;
}
.vanda-window {
  position: fixed;
  bottom: 100px;
  right: 24px;
  z-index: 1001;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}
</style>
```

---

## 📊 API Request/Response Examples

### Request (Non-Streaming)

```json
POST /api/chat
{
  "message": "Parlami dei vostri servizi",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "stream": false,
  "use_rag": true,
  "include_sources": false
}
```

### Response (Non-Streaming)

```json
{
  "session_id": "550e8400-...",
  "message": "Ciao! Presso Vanda Designers offriamo...",
  "sources": null,
  "metadata": {
    "tokens_used": 450,
    "processing_time_ms": 1234,
    "model": "gpt-4o-mini",
    "rag_enabled": true,
    "documents_found": 3
  },
  "timestamp": "2025-11-05T16:00:00Z"
}
```

### Response (Streaming SSE)

```
data: Ciao

data: !

data:  Presso

data:  Vanda

data:  Designers

...

data: [DONE]
```

---

## 🔒 CORS Configuration

Se hai problemi con CORS, aggiorna le variabili ambiente:

```cmd
gcloud run services update vanda-chatbot --region europe-west1 --update-env-vars "ALLOWED_ORIGINS=https://www.agentika.io,https://agentika.io"
```

---

## 📦 Package Dependencies (se usi TypeScript)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "next": "^14.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "typescript": "^5.0.0"
  }
}
```

---

## 🎨 Customizzazione

Puoi personalizzare:
- **Colori**: Cambia `#667eea` e `#764ba2` nel CSS
- **Avatar**: Sostituisci emoji con immagini
- **Stile**: Modifica CSS per matchare il tuo brand
- **Posizionamento**: Floating widget, fullscreen, embedded, etc.

---

## 🐛 Troubleshooting

### Errore CORS
```
Access to fetch blocked by CORS policy
```
**Fix**: Aggiorna `ALLOWED_ORIGINS` su Cloud Run

### Timeout
```
Request timeout
```
**Fix**: Aumenta timeout nel fetch:
```js
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000);

fetch(url, { signal: controller.signal })
```

### Session ID non persistente
**Fix**: Salva session_id in localStorage:
```js
const sessionId = localStorage.getItem('vanda_session') || crypto.randomUUID();
localStorage.setItem('vanda_session', sessionId);
```

---

## 📞 Support

Per problemi:
1. Controlla logs: `gcloud run services logs tail vanda-chatbot --region europe-west1`
2. Testa API: https://vanda-chatbot-515064966632.europe-west1.run.app/docs
3. Health check: https://vanda-chatbot-515064966632.europe-west1.run.app/health

---

**🎉 Happy Coding!**
