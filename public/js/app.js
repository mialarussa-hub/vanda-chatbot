/**
 * VANDA Chatbot - Main Application
 * Logica principale dell'interfaccia chatbot
 */

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const AppState = {
    sessionId: null,
    messages: [],
    isLoading: false,
    messageCount: 0
};

// ============================================================================
// DOM ELEMENTS
// ============================================================================

const DOM = {
    chatMessages: null,
    userInput: null,
    sendBtn: null,
    btnClear: null,
    btnFullscreen: null,
    statMessages: null,
    suggestionBtns: null,
    quickActions: null
};

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Inizializza l'applicazione
 */
function init() {
    // Cache DOM elements
    cacheDOMElements();

    // Setup session
    setupSession();

    // Attach event listeners
    attachEventListeners();

    // Check API health
    checkAPIHealth();

    // Focus input
    DOM.userInput.focus();

    console.log('VANDA Chatbot initialized');
}

/**
 * Memorizza riferimenti agli elementi DOM
 */
function cacheDOMElements() {
    DOM.chatMessages = document.getElementById('chat-messages');
    DOM.userInput = document.getElementById('user-input');
    DOM.sendBtn = document.getElementById('send-btn');
    DOM.btnClear = document.getElementById('btn-clear');
    DOM.btnFullscreen = document.getElementById('btn-fullscreen');
    DOM.statMessages = document.getElementById('stat-messages');
    DOM.suggestionBtns = document.querySelectorAll('.suggestion-btn');
    DOM.quickActions = document.querySelectorAll('.quick-action');
}

/**
 * Setup session ID
 * Genera SEMPRE un nuovo session_id ad ogni caricamento pagina
 */
function setupSession() {
    // Genera nuovo UUID per ogni sessione (refresh = nuova conversazione)
    AppState.sessionId = generateUUID();
    localStorage.setItem(CONFIG.SESSION_STORAGE_KEY, AppState.sessionId);

    console.log('New Session ID:', AppState.sessionId);
}

/**
 * Collega event listeners
 */
function attachEventListeners() {
    // Send button
    DOM.sendBtn.addEventListener('click', handleSendMessage);

    // Input enter key
    DOM.userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !AppState.isLoading) {
            handleSendMessage();
        }
    });

    // Clear chat button
    DOM.btnClear.addEventListener('click', handleClearChat);

    // Fullscreen button
    DOM.btnFullscreen.addEventListener('click', handleToggleFullscreen);

    // Suggestion buttons
    DOM.suggestionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const question = btn.getAttribute('data-question');
            askQuestion(question);
        });
    });

    // Quick action buttons
    DOM.quickActions.forEach(btn => {
        btn.addEventListener('click', () => {
            const question = btn.getAttribute('data-question');
            askQuestion(question);
        });
    });
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Verifica connessione API
 */
async function checkAPIHealth() {
    try {
        const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.HEALTH}`);
        if (response.ok) {
            console.log('✅ API healthy');
        } else {
            console.warn('⚠️ API health check failed');
        }
    } catch (error) {
        console.error('❌ Cannot connect to API:', error);
    }
}

/**
 * Invia messaggio all'API
 */
async function sendMessageToAPI(message) {
    const response = await fetch(`${CONFIG.API_URL}${CONFIG.ENDPOINTS.CHAT}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            session_id: AppState.sessionId,
            ...CONFIG.DEFAULT_REQUEST
        }),
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response;
}

// ============================================================================
// CHAT FUNCTIONS
// ============================================================================

/**
 * Gestisce l'invio del messaggio
 */
async function handleSendMessage() {
    const text = DOM.userInput.value.trim();

    if (!text || AppState.isLoading) return;

    // Valida lunghezza
    if (text.length > CONFIG.MAX_MESSAGE_LENGTH) {
        showError(`Messaggio troppo lungo (max ${CONFIG.MAX_MESSAGE_LENGTH} caratteri)`);
        return;
    }

    // Rimuovi welcome screen
    removeWelcomeScreen();

    // Aggiungi messaggio utente
    addMessage('user', text);

    // Reset input
    DOM.userInput.value = '';
    setLoadingState(true);

    // Mostra typing indicator
    showTypingIndicator();

    try {
        const response = await sendMessageToAPI(text);

        // Rimuovi typing indicator
        hideTypingIndicator();

        // Leggi stream SSE
        await handleStreamResponse(response);

    } catch (error) {
        console.error('Error:', error);
        hideTypingIndicator();
        showError(CONFIG.MESSAGES.ERROR_CONNECTION);
    } finally {
        setLoadingState(false);
    }
}

/**
 * Gestisce risposta streaming
 */
async function handleStreamResponse(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantMessage = '';
    let messageElement = null;
    let chunkCount = 0;
    let buffer = '';

    // Metriche di performance
    const startTime = performance.now();
    let firstChunkTime = null;
    let lastChunkTime = startTime;

    console.log('🔄 Starting SSE stream...');

    try {
        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                const totalTime = performance.now() - startTime;
                console.log(`✅ Stream completed - Chunks: ${chunkCount}, Duration: ${totalTime.toFixed(2)}ms`);

                // Rimuovi cursore streaming
                if (messageElement) {
                    removeStreamingCursor(messageElement);
                }
                break;
            }

            // Traccia timing primo chunk
            if (firstChunkTime === null) {
                firstChunkTime = performance.now();
                const latency = firstChunkTime - startTime;
                console.log(`⚡ First chunk received - Latency: ${latency.toFixed(2)}ms`);
            }

            // Decodifica chunk senza streaming (no {stream: false})
            const chunk = decoder.decode(value, { stream: true });

            // Calcola velocità
            const now = performance.now();
            const chunkInterval = now - lastChunkTime;
            lastChunkTime = now;

            chunkCount++;

            if (CONFIG.DEBUG_STREAMING) {
                console.log(`📦 Chunk ${chunkCount} (Δ${chunkInterval.toFixed(1)}ms):`, chunk.substring(0, 100));
            }

            // Aggiungi al buffer e processa linee complete
            buffer += chunk;
            const lines = buffer.split('\n');

            // Mantieni l'ultima linea incompleta nel buffer
            buffer = lines.pop() || '';

            // Processa linee complete
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const content = line.slice(6);
                    const contentTrimmed = content.trim();

                    // Gestione segnali speciali
                    if (contentTrimmed === '[DONE]') {
                        if (messageElement) {
                            removeStreamingCursor(messageElement);
                        }
                        return;
                    }

                    if (contentTrimmed.startsWith('[ERROR]')) {
                        console.error('❌ Stream error:', contentTrimmed);
                        showError(CONFIG.MESSAGES.ERROR_GENERIC);
                        if (messageElement) {
                            removeStreamingCursor(messageElement);
                        }
                        return;
                    }

                    // Skip segnali sistema
                    if (contentTrimmed.startsWith('[SOURCES]')) {
                        continue;
                    }

                    // Skip chunk vuoti
                    if (contentTrimmed === '') {
                        continue;
                    }

                    // Accumula messaggio preservando gli spazi
                    assistantMessage += content;

                    // Usa requestAnimationFrame per aggiornamento fluido
                    requestAnimationFrame(() => {
                        if (!messageElement) {
                            // Crea messaggio con cursore streaming
                            messageElement = addMessage('assistant', assistantMessage, true);
                        } else {
                            // Aggiorna contenuto in modo ottimizzato
                            updateMessageContentOptimized(messageElement, assistantMessage);
                        }
                    });
                }
            }
        }
    } catch (error) {
        console.error('❌ Stream error:', error);
        if (messageElement) {
            removeStreamingCursor(messageElement);
        }
        throw error;
    }
}

/**
 * Chiedi una domanda pre-impostata
 */
function askQuestion(question) {
    DOM.userInput.value = question;
    handleSendMessage();
}

/**
 * Pulisci chat
 */
function handleClearChat() {
    if (!confirm(CONFIG.MESSAGES.CONFIRM_CLEAR)) return;

    // Nuovo session ID
    AppState.sessionId = generateUUID();
    localStorage.setItem(CONFIG.SESSION_STORAGE_KEY, AppState.sessionId);

    // Reset state
    AppState.messages = [];
    AppState.messageCount = 0;
    DOM.statMessages.textContent = '0';

    // Reset UI
    DOM.chatMessages.innerHTML = `
        <div class="welcome-screen">
            <div class="logo">🏠</div>
            <h3>Nuova Conversazione</h3>
            <p>Come posso aiutarti oggi?</p>
        </div>
    `;

    // Re-attach quick actions
    setTimeout(() => {
        DOM.quickActions = document.querySelectorAll('.quick-action');
        DOM.quickActions.forEach(btn => {
            btn.addEventListener('click', () => {
                const question = btn.getAttribute('data-question');
                askQuestion(question);
            });
        });
    }, 0);

    console.log('Chat cleared, new session:', AppState.sessionId);
}

/**
 * Toggle fullscreen
 */
function handleToggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
}

// ============================================================================
// UI FUNCTIONS
// ============================================================================

/**
 * Aggiungi messaggio alla chat
 */
function addMessage(role, content, isStreaming = false) {
    // Increment counter
    if (role === 'user' || role === 'assistant') {
        AppState.messageCount++;
        DOM.statMessages.textContent = AppState.messageCount;
    }

    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;

    const now = new Date();
    const time = now.toLocaleTimeString('it-IT', {
        hour: '2-digit',
        minute: '2-digit'
    });

    const avatar = role === 'user' ? '👤' : '🤖';
    const escapedContent = escapeHtml(content);

    // Aggiungi cursore streaming se necessario
    const cursorHtml = isStreaming ? '<span class="streaming-cursor"></span>' : '';

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div>
            <div class="message-content">${escapedContent}${cursorHtml}</div>
            <div class="message-time">${time}</div>
        </div>
    `;

    DOM.chatMessages.appendChild(messageDiv);
    scrollToBottom();

    return messageDiv;
}

/**
 * Aggiorna contenuto messaggio (versione legacy)
 */
function updateMessageContent(messageElement, content) {
    const contentDiv = messageElement.querySelector('.message-content');
    contentDiv.textContent = content;
    scrollToBottom();
}

/**
 * Aggiorna contenuto messaggio ottimizzato per streaming
 * Usa textContent diretto per evitare reflow costosi
 */
function updateMessageContentOptimized(messageElement, content) {
    const contentDiv = messageElement.querySelector('.message-content');

    // Trova o crea cursore streaming
    let cursor = contentDiv.querySelector('.streaming-cursor');
    if (!cursor) {
        cursor = document.createElement('span');
        cursor.className = 'streaming-cursor';
        contentDiv.appendChild(cursor);
    }

    // Aggiorna solo il testo, mantenendo il cursore
    const textNode = contentDiv.firstChild;
    if (textNode && textNode.nodeType === Node.TEXT_NODE) {
        textNode.textContent = content;
    } else {
        contentDiv.insertBefore(document.createTextNode(content), cursor);
    }

    // Throttled scroll
    throttledScrollToBottom();
}

/**
 * Rimuove cursore streaming dal messaggio
 */
function removeStreamingCursor(messageElement) {
    const cursor = messageElement.querySelector('.streaming-cursor');
    if (cursor) {
        cursor.remove();
    }
}

/**
 * Mostra typing indicator
 */
function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'typing-indicator';
    indicator.className = 'message';
    indicator.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="typing-indicator">
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    DOM.chatMessages.appendChild(indicator);
    scrollToBottom();
}

/**
 * Nascondi typing indicator
 */
function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

/**
 * Mostra messaggio di errore
 */
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    DOM.chatMessages.appendChild(errorDiv);
    scrollToBottom();

    // Auto-remove dopo timeout
    setTimeout(() => {
        errorDiv.remove();
    }, CONFIG.ERROR_DISPLAY_DURATION);
}

/**
 * Rimuovi welcome screen
 */
function removeWelcomeScreen() {
    const welcomeScreen = DOM.chatMessages.querySelector('.welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.remove();
    }
}

/**
 * Scroll automatico in fondo
 */
function scrollToBottom() {
    setTimeout(() => {
        DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
    }, CONFIG.AUTO_SCROLL_DELAY);
}

/**
 * Throttled scroll per streaming
 * Limita la frequenza di scroll durante streaming per performance
 */
let scrollThrottleTimer = null;
function throttledScrollToBottom() {
    if (scrollThrottleTimer) return;

    scrollThrottleTimer = setTimeout(() => {
        DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
        scrollThrottleTimer = null;
    }, CONFIG.SCROLL_THROTTLE_MS);
}

/**
 * Imposta stato loading
 */
function setLoadingState(loading) {
    AppState.isLoading = loading;
    DOM.userInput.disabled = loading;
    DOM.sendBtn.disabled = loading;

    if (loading) {
        DOM.sendBtn.textContent = '⏳';
    } else {
        DOM.sendBtn.textContent = '📤';
        DOM.userInput.focus();
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Genera UUID v4
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * Escape HTML per prevenire XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// APP INITIALIZATION
// ============================================================================

// Init when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
