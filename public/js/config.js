/**
 * VANDA Chatbot - Configuration
 * Configurazione globale dell'applicazione
 */

const CONFIG = {
    // API Configuration
    API_URL: 'https://vanda-chatbot-515064966632.europe-west1.run.app',
    // API_URL: 'http://localhost:8000',  // LOCALE per test

    // Session Configuration
    SESSION_STORAGE_KEY: 'vanda_session_id',

    // Chat Configuration
    MAX_MESSAGE_LENGTH: 2000,
    TYPING_DELAY: 50, // ms tra caratteri (per effetto typing)

    // UI Configuration
    AUTO_SCROLL_DELAY: 100, // ms
    SCROLL_THROTTLE_MS: 50, // ms - throttle scroll durante streaming
    ERROR_DISPLAY_DURATION: 5000, // ms

    // Debug Configuration
    DEBUG_STREAMING: false, // Imposta true per log dettagliati streaming

    // API Endpoints
    ENDPOINTS: {
        HEALTH: '/health',
        CHAT: '/api/chat',
        CHAT_HEALTH: '/api/chat/health',
        STATS: '/api/chat/stats'
    },

    // Default Request Options
    DEFAULT_REQUEST: {
        stream: true,
        use_rag: true,
        include_sources: false
    },

    // Messages
    MESSAGES: {
        ERROR_CONNECTION: 'Errore di connessione. Verifica la tua connessione e riprova.',
        ERROR_GENERIC: 'Si è verificato un errore. Riprova.',
        CONFIRM_CLEAR: 'Vuoi iniziare una nuova conversazione?',
        TYPING_TEXT: 'Sta scrivendo...'
    }
};

// Export per uso in altri file
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
