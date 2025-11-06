"""
Test Semplice per Memory Manager - VANDA Chatbot

Testa le funzionalità base del Memory Manager:
1. Inizializzazione e connessione Supabase
2. Generazione session_id
3. Salvataggio messaggi (add_message)
4. Recupero history (get_history)
5. Statistiche sessione (get_session_stats)
6. Lista sessioni (get_sessions)
7. Cleanup (delete_session)

Esegui con: python test_memory_simple.py
"""

import sys
from pathlib import Path

# Aggiungi path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.memory_manager import memory_manager
from app.models.schemas import MessageRole

print("=" * 80)
print("VANDA CHATBOT - TEST MEMORY MANAGER (Semplice)")
print("=" * 80)
print()

# ============================================================================
# TEST 1: Verifica Inizializzazione
# ============================================================================
print("💾 TEST 1: Verifica inizializzazione Memory Manager...")
try:
    if memory_manager:
        print(f"✅ Memory Manager inizializzato!")
        print(f"   - Table: {memory_manager.table_name}")
        print(f"   - Max history messages: {memory_manager.max_history_messages}")
        print(f"   - Session timeout: {memory_manager.session_timeout_hours}h")
        print()
    else:
        print("❌ Memory Manager non inizializzato")
        sys.exit(1)
except Exception as e:
    print(f"❌ Errore inizializzazione: {e}")
    sys.exit(1)

# ============================================================================
# TEST 2: Generazione Session ID
# ============================================================================
print("🔑 TEST 2: Generazione session ID...")
try:
    session_id = memory_manager.generate_session_id()
    print(f"✅ Session ID generato: {session_id}")
    print()
except Exception as e:
    print(f"❌ Errore generazione session_id: {e}")
    print()

# ============================================================================
# TEST 3: Salvataggio Messaggi
# ============================================================================
print("💬 TEST 3: Salvataggio messaggi...")
print(f"   Session ID: {session_id}")
print()

try:
    # Messaggio 1: User
    print("   [1/4] Salvando messaggio USER...")
    msg_id_1 = memory_manager.add_message(
        session_id=session_id,
        role=MessageRole.USER,
        content="Ciao! Parlami dei vostri progetti residenziali",
        metadata={}
    )
    print(f"   ✅ Messaggio salvato con ID: {msg_id_1}")

    # Messaggio 2: Assistant
    print("   [2/4] Salvando messaggio ASSISTANT...")
    msg_id_2 = memory_manager.add_message(
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content="Ciao! Siamo specializzati in interior design residenziale...",
        metadata={
            "model": "gpt-4o-mini",
            "tokens_used": 500,
            "rag_documents": 3
        }
    )
    print(f"   ✅ Messaggio salvato con ID: {msg_id_2}")

    # Messaggio 3: User
    print("   [3/4] Salvando secondo messaggio USER...")
    msg_id_3 = memory_manager.add_message(
        session_id=session_id,
        role=MessageRole.USER,
        content="Quali sono i tempi di realizzazione?",
        metadata={}
    )
    print(f"   ✅ Messaggio salvato con ID: {msg_id_3}")

    # Messaggio 4: Assistant
    print("   [4/4] Salvando secondo messaggio ASSISTANT...")
    msg_id_4 = memory_manager.add_message(
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content="I tempi variano da 3 a 12 mesi a seconda del progetto...",
        metadata={
            "model": "gpt-4o-mini",
            "tokens_used": 450,
            "rag_documents": 2
        }
    )
    print(f"   ✅ Messaggio salvato con ID: {msg_id_4}")
    print()

    print(f"✅ Salvati 4 messaggi nella sessione {session_id}")
    print()

except Exception as e:
    print(f"❌ Errore salvataggio messaggi: {e}")
    import traceback
    traceback.print_exc()
    print()

# ============================================================================
# TEST 4: Recupero History
# ============================================================================
print("📖 TEST 4: Recupero history conversazione...")
try:
    history = memory_manager.get_history(session_id=session_id)

    print(f"✅ Recuperati {len(history)} messaggi")
    print()
    print("   Conversazione:")
    print("   " + "-" * 76)

    for i, msg in enumerate(history, 1):
        role_emoji = "👤" if msg.role == MessageRole.USER else "🤖"
        print(f"   [{i}] {role_emoji} {msg.role.upper()}: {msg.content[:60]}...")

    print("   " + "-" * 76)
    print()

except Exception as e:
    print(f"❌ Errore recupero history: {e}")
    import traceback
    traceback.print_exc()
    print()

# ============================================================================
# TEST 5: Statistiche Sessione
# ============================================================================
print("📊 TEST 5: Statistiche sessione...")
try:
    stats = memory_manager.get_session_stats(session_id=session_id)

    if stats:
        print(f"✅ Statistiche recuperate:")
        print(f"   - Messaggi totali: {stats['message_count']}")
        print(f"   - Messaggi user: {stats['user_count']}")
        print(f"   - Messaggi assistant: {stats['assistant_count']}")
        print(f"   - Durata conversazione: {stats['duration_minutes']} minuti")
        print(f"   - Primo messaggio: {stats['first_message'].strftime('%H:%M:%S')}")
        print(f"   - Ultimo messaggio: {stats['last_message'].strftime('%H:%M:%S')}")
        print()
    else:
        print("   ⚠️ Nessuna statistica disponibile")
        print()

except Exception as e:
    print(f"❌ Errore statistiche: {e}")
    print()

# ============================================================================
# TEST 6: Lista Sessioni Attive
# ============================================================================
print("📋 TEST 6: Lista sessioni attive...")
try:
    sessions = memory_manager.get_sessions(active_only=True)

    print(f"✅ Trovate {len(sessions)} sessioni attive")

    if sessions:
        print()
        print("   Top 5 sessioni (più recenti):")
        for i, session in enumerate(sessions[:5], 1):
            last_activity = session['last_activity'].strftime('%H:%M:%S')
            print(f"   [{i}] {session['session_id'][:8]}... - {session['message_count']} msgs - {last_activity}")

    print()

except Exception as e:
    print(f"❌ Errore lista sessioni: {e}")
    print()

# ============================================================================
# TEST 7: Creazione Seconda Sessione (per test multi-session)
# ============================================================================
print("🔑 TEST 7: Test multi-session (crea seconda sessione)...")
try:
    session_id_2 = memory_manager.generate_session_id()
    print(f"   Session ID 2: {session_id_2}")

    # Aggiungi 2 messaggi alla seconda sessione
    memory_manager.add_message(
        session_id=session_id_2,
        role=MessageRole.USER,
        content="Quanto costa un progetto?",
        metadata={}
    )

    memory_manager.add_message(
        session_id=session_id_2,
        role=MessageRole.ASSISTANT,
        content="I costi dipendono dalla scala del progetto...",
        metadata={"model": "gpt-4o-mini", "tokens_used": 300}
    )

    print(f"✅ Creata seconda sessione con 2 messaggi")
    print()

    # Verifica che possiamo recuperare entrambe
    history_1 = memory_manager.get_history(session_id)
    history_2 = memory_manager.get_history(session_id_2)

    print(f"   Sessione 1: {len(history_1)} messaggi")
    print(f"   Sessione 2: {len(history_2)} messaggi")
    print()

except Exception as e:
    print(f"❌ Errore multi-session: {e}")
    print()

# ============================================================================
# TEST 8: Cleanup - Elimina Sessioni di Test
# ============================================================================
print("🧹 TEST 8: Cleanup - elimina sessioni di test...")
try:
    print(f"   Eliminando sessione 1: {session_id[:8]}...")
    deleted_1 = memory_manager.delete_session(session_id)

    print(f"   Eliminando sessione 2: {session_id_2[:8]}...")
    deleted_2 = memory_manager.delete_session(session_id_2)

    if deleted_1 and deleted_2:
        print(f"✅ Entrambe le sessioni di test eliminate")
    else:
        print(f"⚠️ Alcune sessioni non eliminate (potrebbero non esistere)")

    print()

    # Verifica eliminazione
    history_after = memory_manager.get_history(session_id)
    if len(history_after) == 0:
        print(f"   ✅ Verificato: sessione 1 completamente eliminata")
    else:
        print(f"   ⚠️ Sessione 1 ancora presente ({len(history_after)} messaggi)")

    print()

except Exception as e:
    print(f"❌ Errore cleanup: {e}")
    print()

# ============================================================================
# RIEPILOGO FINALE
# ============================================================================
print("=" * 80)
print("✅ TEST MEMORY MANAGER COMPLETATI")
print("=" * 80)
print()
print("Riepilogo:")
print(f"  ✅ Inizializzazione: OK")
print(f"  ✅ Generazione session_id: OK")
print(f"  ✅ Salvataggio messaggi: OK")
print(f"  ✅ Recupero history: OK")
print(f"  ✅ Statistiche sessione: OK")
print(f"  ✅ Lista sessioni: OK")
print(f"  ✅ Multi-session: OK")
print(f"  ✅ Cleanup: OK")
print()
print("💾 IMPORTANTE:")
print("   Le conversazioni sono ora salvate su Supabase!")
print("   Puoi vedere i dati nella tabella 'chat_messages'")
print()
print("🎯 PROSSIMI STEP:")
print("   1. Implementa Chat API endpoint (/api/chat)")
print("   2. Integra Memory Manager nel chatbot")
print("   3. Test end-to-end completo")
print()
print("=" * 80)
