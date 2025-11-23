/**
 * VANDA Voice Manager WebSocket
 * Gestisce Voice Recognition (STT) e Text-to-Speech (TTS) via WebSocket
 * 
 * Features:
 * - Full-duplex communication
 * - Real-time audio streaming
 * - Echo cancellation (Stop STT while speaking)
 */

const VoiceManagerWS = {
    // ========================================================================
    // STATE
    // ========================================================================

    enabled: false,
    state: 'idle', // idle | listening | thinking | speaking
    recognition: null,
    socket: null,
    audioContext: null,
    audioQueue: [],
    isPlaying: false,
    nextStartTime: 0,

    // Configurazione
    config: {
        wsUrl: (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws/chat',
        silenceTimeout: 1000,
    },

    // Callbacks
    onStateChange: null,
    onTranscript: null,

    // ========================================================================
    // INITIALIZATION
    // ========================================================================

    init() {
        console.log('🎤 VoiceManagerWS: Initializing...');

        // Check browser support
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.error('❌ Speech Recognition not supported');
            return false;
        }

        // Setup AudioContext for playback
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();

        // Setup Speech Recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = false;
        this.recognition.lang = 'it-IT';

        this.recognition.onstart = () => {
            console.log('🎤 Recognition started');
            if (this.state !== 'speaking') {
                this.setState('listening');
            }
        };

        this.recognition.onresult = (event) => {
            const result = event.results[event.results.length - 1];
            if (result.isFinal) {
                const transcript = result[0].transcript.trim();
                console.log('🎤 Transcript:', transcript);

                if (transcript) {
                    this.sendUserMessage(transcript);
                }
            }
        };

        this.recognition.onerror = (event) => {
            console.error('🎤 Recognition error:', event.error);
            if (event.error === 'not-allowed') {
                this.disable();
            }
        };

        this.recognition.onend = () => {
            console.log('🎤 Recognition ended');
            // Auto-restart if enabled and not speaking
            if (this.enabled && this.state !== 'speaking') {
                setTimeout(() => {
                    try { this.recognition.start(); } catch (e) { }
                }, 100);
            }
        };

        console.log('✅ VoiceManagerWS initialized');
        return true;
    },

    // ========================================================================
    // WEBSOCKET CONNECTION
    // ========================================================================

    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) return;

        console.log('🔌 Connecting to WebSocket:', this.config.wsUrl);
        this.socket = new WebSocket(this.config.wsUrl);
        this.socket.binaryType = 'arraybuffer'; // Important for audio chunks

        this.socket.onopen = () => {
            console.log('✅ WebSocket connected');
        };

        this.socket.onmessage = async (event) => {
            if (event.data instanceof ArrayBuffer) {
                // Audio chunk received
                this.handleAudioChunk(event.data);
            } else {
                // JSON control message
                const msg = JSON.parse(event.data);
                this.handleControlMessage(msg);
            }
        };

        this.socket.onclose = () => {
            console.log('🔌 WebSocket disconnected');
            // Auto-reconnect after delay
            setTimeout(() => this.connect(), 3000);
        };
    },

    // ========================================================================
    // MESSAGE HANDLING
    // ========================================================================

    sendUserMessage(text) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.warn('⚠️ WebSocket not connected');
            return;
        }

        this.setState('thinking');

        // Send to backend
        this.socket.send(JSON.stringify({
            message: text,
            session_id: localStorage.getItem('vanda_session_id')
        }));

        // Update UI (simulate user message)
        if (window.addMessage) {
            window.addMessage('user', text);
        }
    },

    handleControlMessage(msg) {
        switch (msg.type) {
            case 'control':
                if (msg.signal === 'start_speaking') {
                    this.handleStartSpeaking();
                } else if (msg.signal === 'stop_speaking') {
                    this.handleStopSpeaking();
                }
                break;

            case 'text_chunk':
                // Update UI streaming
                // This assumes app.js exposes a way to stream text
                // For now we just log it, as audio is the priority
                break;

            case 'session_init':
                localStorage.setItem('vanda_session_id', msg.session_id);
                break;
        }
    },

    // ========================================================================
    // ECHO CANCELLATION (CRITICAL)
    // ========================================================================

    handleStartSpeaking() {
        console.log('🔇 Bot started speaking - Pausing mic');
        this.setState('speaking');

        // Stop recognition to prevent self-listening
        if (this.recognition) {
            this.recognition.stop();
        }
    },

    handleStopSpeaking() {
        console.log('🎤 Bot stopped speaking - Resuming mic');
        this.setState('listening');

        // Resume recognition
        if (this.enabled) {
            try { this.recognition.start(); } catch (e) { }
        }
    },

    // ========================================================================
    // AUDIO PLAYBACK (Low Latency)
    // ========================================================================

    async handleAudioChunk(arrayBuffer) {
        try {
            // Decode audio data
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            this.playAudioBuffer(audioBuffer);
        } catch (e) {
            console.error('❌ Error decoding audio chunk:', e);
        }
    },

    playAudioBuffer(buffer) {
        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(this.audioContext.destination);

        // Schedule playback
        // If nextStartTime is in the past, reset it to now
        const now = this.audioContext.currentTime;
        if (this.nextStartTime < now) {
            this.nextStartTime = now;
        }

        source.start(this.nextStartTime);

        // Advance time for next chunk
        this.nextStartTime += buffer.duration;
    },

    // ========================================================================
    // PUBLIC API
    // ========================================================================

    toggle() {
        if (this.enabled) {
            this.disable();
        } else {
            this.enable();
        }
    },

    enable() {
        this.enabled = true;
        this.connect(); // Ensure WS is connected

        // Resume AudioContext (needed for browsers)
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }

        try {
            this.recognition.start();
        } catch (e) {
            console.log('Recognition already started');
        }

        this.setState('listening');
    },

    disable() {
        this.enabled = false;
        this.recognition.stop();
        this.setState('idle');
    },

    setState(newState) {
        if (this.state !== newState) {
            this.state = newState;
            if (this.onStateChange) {
                this.onStateChange(newState);
            }
        }
    }
};

// Auto-init
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => VoiceManagerWS.init());
} else {
    VoiceManagerWS.init();
}
