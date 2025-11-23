"""
Test rapido per ElevenLabs TTS endpoint.

Verifica che:
1. La configurazione sia corretta
2. L'API key funzioni
3. La generazione TTS produca audio valido
"""

import sys
import os
import time

# Assicurati che il path del progetto sia nel PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings
from app.api.voice import call_elevenlabs_tts_stream

def test_elevenlabs_config():
    """Test configurazione ElevenLabs"""
    print("=" * 80)
    print("TEST 1: Configurazione ElevenLabs")
    print("=" * 80)

    print(f"API Key presente: {'YES' if settings.ELEVENLABS_API_KEY else 'NO'}")
    print(f"API Key (primi 10 char): {settings.ELEVENLABS_API_KEY[:10]}...")
    print(f"Voice ID: {settings.ELEVENLABS_VOICE_ID}")
    print(f"Model ID: {settings.ELEVENLABS_MODEL_ID}")
    print()

    if not settings.ELEVENLABS_API_KEY:
        print("ERRORE: ELEVENLABS_API_KEY non configurata!")
        return False

    print("Configurazione OK!\n")
    return True


def test_tts_generation():
    """Test generazione TTS con testo italiano"""
    print("=" * 80)
    print("TEST 2: Generazione TTS")
    print("=" * 80)

    test_text = "Ciao! Sono Vanda, il tuo assistente virtuale per interior design."
    print(f"Testo di test: '{test_text}'")
    print(f"Lunghezza: {len(test_text)} caratteri")
    print()

    try:
        print("Chiamata a ElevenLabs API (Streaming)...")
        start_time = time.time()
        
        # Generator
        audio_stream = call_elevenlabs_tts_stream(
            text=test_text,
            voice_id=settings.ELEVENLABS_VOICE_ID,
            model_id=settings.ELEVENLABS_MODEL_ID,
            voice_settings={
                "stability": 0.5,
                "similarity_boost": 0.8,
                "use_speaker_boost": True,
                "speed": 1.0
            }
        )
        
        # Consume stream
        audio_data = b""
        chunk_count = 0
        first_byte_time = None
        
        for chunk in audio_stream:
            if not first_byte_time:
                first_byte_time = time.time()
                print(f"  ⏱️ Time to first byte: {(first_byte_time - start_time)*1000:.0f}ms")
            
            audio_data += chunk
            chunk_count += 1
            print(f"  📦 Received chunk {chunk_count}: {len(chunk)} bytes", end="\r")
            
        print(f"\n✅ Stream completato: {chunk_count} chunks, {len(audio_data)} bytes totali")
        
        # Verifica formato (header MP3)
        if len(audio_data) > 3:
            if audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
                print("✅ Formato MP3 rilevato")
            else:
                print("WARN: Il formato audio potrebbe non essere MP3")

        # Salva file
        output_file = "test_elevenlabs_output.mp3"
        with open(output_file, "wb") as f:
            f.write(audio_data)
        
        print(f"\nAudio salvato in: {output_file}")
        print("Puoi ascoltarlo per verificare la qualita!")
        print()

        return True

    except Exception as e:
        print(f"\nERRORE durante generazione TTS: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Esegue tutti i test"""
    print("\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "  TEST ELEVENLABS TTS INTEGRATION".center(78) + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)
    print("\n")

    # Test 1: Configurazione
    if not test_elevenlabs_config():
        print("\nTest FALLITO - Configurazione non valida")
        sys.exit(1)

    # Test 2: Generazione TTS
    if not test_tts_generation():
        print("\nTest FALLITO - Errore durante generazione TTS")
        sys.exit(1)

    # Tutti i test passati
    print("=" * 80)
    print("SUCCESSO! Tutti i test passati!")
    print("=" * 80)
    print()
    print("PROSSIMI PASSI:")
    print("1. Ascolta il file test_elevenlabs_output.mp3 per verificare la qualita")
    print("2. Se OK, procedi con il deploy su Cloud Run")
    print("3. Testa l'endpoint /api/voice/tts-chunk in produzione")
    print()


if __name__ == "__main__":
    main()
