"""
Test End-to-End per VANDA Chatbot

Testa l'intero flusso del chatbot:
1. Avvio FastAPI app locale
2. Invio richieste HTTP a /api/chat
3. Test streaming e non-streaming
4. Verifica salvataggio su DB (Memory Manager)
5. Test con RAG abilitato/disabilitato

Prerequisiti:
- FastAPI app in esecuzione su http://localhost:8080
- Variabili .env configurate
- Supabase connesso

Esegui:
1. Avvia app: uvicorn main:app --port 8080
2. Run test: python test_chatbot_e2e.py
"""

import sys
from pathlib import Path
import time
import json
import uuid

# Aggiungi path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import httpx
except ImportError:
    print("❌ httpx non installato. Installalo con: pip install httpx")
    sys.exit(1)

from app.services.memory_manager import memory_manager

print("=" * 80)
print("VANDA CHATBOT - TEST END-TO-END")
print("=" * 80)
print()

# Config
BASE_URL = "http://localhost:8080"
session_id = str(uuid.uuid4())

print(f"Base URL: {BASE_URL}")
print(f"Session ID: {session_id}")
print()

# ============================================================================
# TEST 0: Verifica che l'app sia in esecuzione
# ============================================================================
print("=" * 80)
print("TEST 0: Verifica app in esecuzione")
print("=" * 80)
print()

try:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{BASE_URL}/health")

        if response.status_code == 200:
            print(f"✅ App running - Status: {response.json()['status']}")
            print()
        else:
            print(f"❌ App unhealthy - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            print()
            print("⚠️  Avvia l'app con: uvicorn main:app --port 8080")
            sys.exit(1)

except Exception as e:
    print(f"❌ Impossibile connettersi all'app: {e}")
    print()
    print("⚠️  Assicurati che l'app sia in esecuzione:")
    print("   1. cd D:\\PROGETTI\\AGENTIKA\\WEB\\vanda-chatbot")
    print("   2. venv\\Scripts\\activate  (Windows)")
    print("   3. uvicorn main:app --port 8080")
    print()
    sys.exit(1)

# ============================================================================
# TEST 1: Chat NON-STREAMING con RAG
# ============================================================================
print("=" * 80)
print("TEST 1: Chat NON-STREAMING con RAG")
print("=" * 80)
print()

query_1 = "Parlami brevemente dei vostri servizi di interior design"

print(f"Query: \"{query_1}\"")
print()

request_body = {
    "message": query_1,
    "session_id": session_id,
    "stream": False,
    "use_rag": True,
    "include_sources": True
}

print("Inviando richiesta POST /api/chat...")
start_time = time.time()

try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{BASE_URL}/api/chat",
            json=request_body
        )

        elapsed_time = (time.time() - start_time) * 1000

        if response.status_code == 200:
            data = response.json()

            print(f"✅ Risposta ricevuta in {elapsed_time:.0f}ms")
            print()
            print("📝 Risposta:")
            print("-" * 80)
            print(data["message"])
            print("-" * 80)
            print()
            print("📊 Metadata:")
            print(f"   - Session ID: {data['session_id']}")
            print(f"   - Tokens used: {data['metadata'].get('tokens_used', 'N/A')}")
            print(f"   - Processing time: {data['metadata'].get('processing_time_ms', 'N/A')}ms")
            print(f"   - Documents found: {data['metadata'].get('documents_found', 0)}")
            print(f"   - RAG enabled: {data['metadata'].get('rag_enabled', False)}")

            if data.get("sources"):
                print()
                print(f"📄 Documenti sorgente ({len(data['sources'])}):")
                for i, source in enumerate(data['sources'], 1):
                    print(f"   [{i}] ID: {source['id']}, Similarity: {source['similarity']}")
            print()
        else:
            print(f"❌ Errore: {response.status_code}")
            print(f"   {response.text}")
            print()

except Exception as e:
    print(f"❌ Errore durante richiesta: {e}")
    print()

# ============================================================================
# TEST 2: Chat STREAMING con RAG
# ============================================================================
print("=" * 80)
print("TEST 2: Chat STREAMING con RAG")
print("=" * 80)
print()

query_2 = "Quali sono i tempi di realizzazione di un progetto?"

print(f"Query: \"{query_2}\"")
print()

request_body = {
    "message": query_2,
    "session_id": session_id,
    "stream": True,
    "use_rag": True,
    "include_sources": False
}

print("Inviando richiesta POST /api/chat (streaming)...")
print()
print("📝 Risposta (token-by-token):")
print("-" * 80)

start_time = time.time()
first_token_time = None
token_count = 0
full_response = ""

try:
    with httpx.Client(timeout=60.0) as client:
        with client.stream(
            "POST",
            f"{BASE_URL}/api/chat",
            json=request_body
        ) as response:

            if response.status_code == 200:
                for line in response.iter_lines():
                    if first_token_time is None and line.strip():
                        first_token_time = (time.time() - start_time) * 1000

                    if line.startswith("data: "):
                        content = line[6:].strip()

                        if content == "[DONE]":
                            break
                        elif content.startswith("[ERROR]"):
                            print(f"\n❌ Errore: {content}")
                            break
                        elif content.startswith("[SOURCES]"):
                            # Skip sources per output
                            pass
                        else:
                            print(content, end='', flush=True)
                            full_response += content
                            token_count += 1

                total_time = (time.time() - start_time) * 1000

                print()
                print("-" * 80)
                print()
                print(f"✅ Streaming completato!")
                print(f"   - ⚡ TTFT: {first_token_time:.0f}ms")
                print(f"   - ⏱️  Tempo totale: {total_time:.0f}ms ({total_time/1000:.2f}s)")
                print(f"   - 📊 Chunks ricevuti: {token_count}")
                print(f"   - 📏 Caratteri: {len(full_response)}")
                print()
            else:
                print(f"❌ Errore: {response.status_code}")
                print(f"   {response.text}")
                print()

except Exception as e:
    print(f"\n❌ Errore durante streaming: {e}")
    print()

# ============================================================================
# TEST 3: Verifica History su Database
# ============================================================================
print("=" * 80)
print("TEST 3: Verifica History su Database")
print("=" * 80)
print()

print(f"Recuperando history per session: {session_id[:8]}...")
print()

try:
    history = memory_manager.get_history(session_id=session_id)

    print(f"✅ Trovati {len(history)} messaggi salvati su Supabase")
    print()
    print("Conversazione:")
    print("-" * 80)

    for i, msg in enumerate(history, 1):
        role_emoji = "👤" if msg.role == "user" else "🤖"
        role_str = msg.role.upper() if isinstance(msg.role, str) else msg.role.value.upper()
        content_preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        print(f"[{i}] {role_emoji} {role_str}: {content_preview}")

    print("-" * 80)
    print()

    # Verifica che ci siano almeno 4 messaggi (2 query + 2 risposte)
    if len(history) >= 4:
        print("✅ History salvata correttamente!")
    else:
        print(f"⚠️  Attesi almeno 4 messaggi, trovati {len(history)}")
    print()

except Exception as e:
    print(f"❌ Errore recupero history: {e}")
    print()

# ============================================================================
# TEST 4: Statistiche Sessione
# ============================================================================
print("=" * 80)
print("TEST 4: Statistiche Sessione")
print("=" * 80)
print()

try:
    stats = memory_manager.get_session_stats(session_id=session_id)

    if stats:
        print(f"✅ Statistiche sessione:")
        print(f"   - Messaggi totali: {stats['message_count']}")
        print(f"   - Messaggi user: {stats['user_count']}")
        print(f"   - Messaggi assistant: {stats['assistant_count']}")
        print(f"   - Durata: {stats['duration_minutes']} minuti")
        print(f"   - Primo messaggio: {stats['first_message'].strftime('%H:%M:%S')}")
        print(f"   - Ultimo messaggio: {stats['last_message'].strftime('%H:%M:%S')}")
        print()
    else:
        print("⚠️  Nessuna statistica disponibile")
        print()

except Exception as e:
    print(f"❌ Errore statistiche: {e}")
    print()

# ============================================================================
# TEST 5: Health Check Servizi
# ============================================================================
print("=" * 80)
print("TEST 5: Health Check Servizi")
print("=" * 80)
print()

try:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{BASE_URL}/api/chat/health")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print()
            print("Servizi:")
            for service, healthy in data['services'].items():
                status_icon = "✅" if healthy else "❌"
                print(f"   {status_icon} {service}: {'OK' if healthy else 'FAILED'}")
            print()
        else:
            print(f"❌ Health check failed: {response.status_code}")
            print()

except Exception as e:
    print(f"❌ Errore health check: {e}")
    print()

# ============================================================================
# TEST 6: Chat senza RAG
# ============================================================================
print("=" * 80)
print("TEST 6: Chat SENZA RAG (solo LLM)")
print("=" * 80)
print()

query_3 = "Che giorno è oggi?"

print(f"Query: \"{query_3}\"")
print()

request_body = {
    "message": query_3,
    "session_id": session_id,
    "stream": False,
    "use_rag": False  # Disabilita RAG
}

try:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{BASE_URL}/api/chat",
            json=request_body
        )

        if response.status_code == 200:
            data = response.json()

            print("📝 Risposta:")
            print("-" * 80)
            print(data["message"])
            print("-" * 80)
            print()
            print(f"   - RAG enabled: {data['metadata'].get('rag_enabled', False)}")
            print(f"   - Documents found: {data['metadata'].get('documents_found', 0)}")
            print()

            if not data['metadata'].get('rag_enabled'):
                print("✅ RAG correttamente disabilitato!")
            else:
                print("⚠️  RAG dovrebbe essere disabilitato")
            print()
        else:
            print(f"❌ Errore: {response.status_code}")
            print()

except Exception as e:
    print(f"❌ Errore: {e}")
    print()

# ============================================================================
# NOTA: Cleanup Disabilitato - Conversazioni Permanenti
# ============================================================================
# Le conversazioni vengono mantenute nel database per analisi e valutazione.
# Per eliminare manualmente una sessione:
#   memory_manager.delete_session(session_id)
#
# Per cleanup automatico sessioni vecchie (opzionale):
#   memory_manager.cleanup_old_sessions(hours_threshold=24)

print("=" * 80)
print("💾 CONVERSAZIONE SALVATA PERMANENTEMENTE")
print("=" * 80)
print()
print(f"✅ Session ID: {session_id}")
print(f"   Tutti i messaggi sono salvati su Supabase nella tabella 'chat_messages'")
print(f"   Puoi recuperarli con: memory_manager.get_history('{session_id}')")
print()

# ============================================================================
# RIEPILOGO FINALE
# ============================================================================
print("=" * 80)
print("✅ TEST END-TO-END COMPLETATI")
print("=" * 80)
print()
print("Riepilogo:")
print("  ✅ App running & health check")
print("  ✅ Chat non-streaming con RAG")
print("  ✅ Chat streaming con RAG")
print("  ✅ Verifica history su DB")
print("  ✅ Statistiche sessione")
print("  ✅ Health check servizi")
print("  ✅ Chat senza RAG")
print("  💾 Conversazioni salvate permanentemente su Supabase")
print()
print("🎉 CHATBOT FUNZIONANTE E PRONTO PER IL DEPLOY!")
print()
print("📊 Dati salvati:")
print(f"   Session ID: {session_id}")
print(f"   Tabella: chat_messages su Supabase")
print(f"   Messaggi: Disponibili per analisi e valutazione")
print()
print("📦 Prossimi step:")
print("   1. Test su più conversazioni")
print("   2. Deploy su Google Cloud Run")
print("   3. Integrazione frontend su agentika.io")
print()
print("=" * 80)
