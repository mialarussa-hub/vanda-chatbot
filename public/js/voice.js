/**
 * VANDA Voice Manager
 * Gestisce Voice Recognition (STT) e Text-to-Speech (TTS) real-time
 */

const VoiceManager = {
    // ========================================================================
    // STATE
    // ========================================================================

    enabled: false,
    state: 'idle', // idle | listening | thinking | speaking
    recognition: null,
    audioQueue: [],
    currentAudio: null,
    isPlaying: false,

    // Buffer per accumulo testo durante streaming
    textBuffer: '',
    lastChunkTime: null,
    chunkTimeout: null,

    // Configurazione
    config: {
        voice: 'nova',
        model: 'tts-1',
        speed: 1.0,
        silenceTimeout: 1500, // ms di silenzio prima auto-submit
        minChunkWords: 15, // Parole minime per chunk TTS
        chunkTimeoutMs: 2000 // Timeout per forzare invio chunk
    },

    // Callbacks
    onTranscript: null, // Chiamata quando speech-to-text è pronto
    onStateChange: null, // Chiamata quando cambia stato

    // ========================================================================
    // INITIALIZATION
    // ========================================================================

    init() {
        console.log('🎤 VoiceManager: Initializing...');

        // Check browser support
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.error('❌ Speech Recognition not supported in this browser');
            return false;
        }

        // Setup Speech Recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();

        this.recognition.continuous = true; // Continuous listening
        this.recognition.interimResults = false; // Only final results
        this.recognition.lang = 'it-IT'; // Italian
        this.recognition.maxAlternatives = 1;

        // Event handlers
        this.recognition.onstart = () => {
            console.log('🎤 Recognition started');
            this.setState('listening');
        };

        this.recognition.onresult = (event) => {
            const result = event.results[event.results.length - 1];
            if (result.isFinal) {
                const transcript = result[0].transcript;
                console.log('🎤 Transcript:', transcript);

                // Call callback with transcript
                if (this.onTranscript) {
                    this.onTranscript(transcript);
                }
            }
        };

        this.recognition.onerror = (event) => {
            console.error('🎤 Recognition error:', event.error);
            if (event.error === 'no-speech') {
                // Nessun parlato rilevato, continua ad ascoltare
                return;
            }
            this.setState('idle');
        };

        this.recognition.onend = () => {
            console.log('🎤 Recognition ended');
            // Se voice mode è ancora attivo, riavvia
            if (this.enabled && this.state === 'listening') {
                setTimeout(() => this.recognition.start(), 100);
            } else {
                this.setState('idle');
            }
        };

        console.log('✅ VoiceManager initialized');
        return true;
    },

    // ========================================================================
    // SPEECH TO TEXT (STT)
    // ========================================================================

    startListening() {
        if (!this.recognition) {
            console.error('❌ Recognition not initialized');
            return false;
        }

        try {
            this.enabled = true;
            this.recognition.start();
            return true;
        } catch (e) {
            console.error('❌ Failed to start recognition:', e);
            return false;
        }
    },

    stopListening() {
        if (this.recognition) {
            this.enabled = false;
            this.recognition.stop();
        }
        this.setState('idle');
    },

    // ========================================================================
    // TEXT TO SPEECH (TTS) - CHUNKED REAL-TIME
    // ========================================================================

    /**
     * Processa chunk di streaming LLM per TTS real-time
     * @param {string} chunk - Nuovo chunk di testo dallo streaming
     */
    async processStreamingChunk(chunk) {
        // Accumula nel buffer
        this.textBuffer += chunk;
        this.lastChunkTime = Date.now();

        // Clear timeout esistente
        if (this.chunkTimeout) {
            clearTimeout(this.chunkTimeout);
        }

        // Check se abbiamo abbastanza per inviare a TTS
        if (this.shouldSendChunk(this.textBuffer)) {
            await this.sendChunkToTTS(this.textBuffer);
            this.textBuffer = '';
        } else {
            // Imposta timeout per forzare invio se non arrivano altri chunk
            this.chunkTimeout = setTimeout(async () => {
                if (this.textBuffer.trim().length > 0) {
                    await this.sendChunkToTTS(this.textBuffer);
                    this.textBuffer = '';
                }
            }, this.config.chunkTimeoutMs);
        }
    },

    /**
     * Determina se il buffer contiene abbastanza testo per chunk TTS
     */
    shouldSendChunk(text) {
        // Invia se:
        // 1. Trova fine frase (. ! ? seguito da spazio)
        if (/[.!?]\s/.test(text)) {
            return true;
        }

        // 2. Supera parole minime
        const wordCount = text.trim().split(/\s+/).length;
        if (wordCount >= this.config.minChunkWords) {
            return true;
        }

        return false;
    },

    /**
     * Invia chunk di testo a TTS API e accoda audio
     */
    async sendChunkToTTS(text) {
        if (!text || text.trim().length === 0) return;

        console.log(`🔊 Generating TTS for chunk: "${text.substring(0, 50)}..."`);

        try {
            const response = await fetch(`${CONFIG.API_URL}/api/voice/tts-chunk`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: text.trim(),
                    voice: this.config.voice,
                    model: this.config.model,
                    speed: this.config.speed
                })
            });

            if (!response.ok) {
                throw new Error(`TTS API error: ${response.status}`);
            }

            // Get audio blob
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            console.log('✅ TTS chunk ready, adding to queue');

            // Aggiungi a queue
            this.audioQueue.push(audioUrl);

            // Start playback se non già in corso
            if (!this.isPlaying) {
                this.playNextInQueue();
            }

        } catch (error) {
            console.error('❌ TTS error:', error);
        }
    },

    /**
     * Riproduce prossimo audio in queue
     */
    playNextInQueue() {
        if (this.audioQueue.length === 0) {
            this.isPlaying = false;
            // Se non ci sono più chunk in arrivo, torna a listening
            if (this.enabled && this.state === 'speaking') {
                this.setState('listening');
            }
            return;
        }

        this.isPlaying = true;
        this.setState('speaking');

        const audioUrl = this.audioQueue.shift();

        // Create audio element
        const audio = new Audio(audioUrl);
        this.currentAudio = audio;

        // When audio ends, play next
        audio.onended = () => {
            URL.revokeObjectURL(audioUrl); // Cleanup
            this.currentAudio = null;
            this.playNextInQueue(); // Recursive: play next
        };

        audio.onerror = (e) => {
            console.error('❌ Audio playback error:', e);
            URL.revokeObjectURL(audioUrl);
            this.currentAudio = null;
            this.playNextInQueue(); // Skip and play next
        };

        // Play
        audio.play().catch(e => {
            console.error('❌ Failed to play audio:', e);
            this.playNextInQueue();
        });
    },

    /**
     * Chiamata quando streaming LLM termina
     * Invia eventuale testo residuo nel buffer
     */
    async finishStreaming() {
        // Clear timeout
        if (this.chunkTimeout) {
            clearTimeout(this.chunkTimeout);
            this.chunkTimeout = null;
        }

        // Invia eventuale testo rimasto nel buffer
        if (this.textBuffer.trim().length > 0) {
            await this.sendChunkToTTS(this.textBuffer);
            this.textBuffer = '';
        }

        // Se non sta già parlando e non ci sono audio in queue, torna a listening
        if (!this.isPlaying && this.audioQueue.length === 0 && this.enabled) {
            this.setState('listening');
        }
    },

    /**
     * Stop playback e svuota queue
     */
    stopPlayback() {
        // Stop current audio
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }

        // Clear queue
        this.audioQueue.forEach(url => URL.revokeObjectURL(url));
        this.audioQueue = [];
        this.isPlaying = false;

        // Clear buffer
        this.textBuffer = '';
        if (this.chunkTimeout) {
            clearTimeout(this.chunkTimeout);
            this.chunkTimeout = null;
        }
    },

    // ========================================================================
    // STATE MANAGEMENT
    // ========================================================================

    setState(newState) {
        if (this.state !== newState) {
            console.log(`🔄 Voice state: ${this.state} → ${newState}`);
            this.state = newState;

            if (this.onStateChange) {
                this.onStateChange(newState);
            }
        }
    },

    toggle() {
        if (this.enabled) {
            this.disable();
        } else {
            this.enable();
        }
    },

    enable() {
        console.log('🎤 Enabling voice mode');
        this.enabled = true;
        this.startListening();
    },

    disable() {
        console.log('🔇 Disabling voice mode');
        this.enabled = false;
        this.stopListening();
        this.stopPlayback();
        this.setState('idle');
    },

    reset() {
        this.disable();
        this.textBuffer = '';
        if (this.chunkTimeout) {
            clearTimeout(this.chunkTimeout);
            this.chunkTimeout = null;
        }
    }
};

// Auto-initialize when script loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => VoiceManager.init());
} else {
    VoiceManager.init();
}
