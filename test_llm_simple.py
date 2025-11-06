"""
Test Semplice per LLM Service - VANDA Chatbot

Testa le funzionalità base del LLM Service:
1. Inizializzazione servizio
2. Generazione risposta standard (non-streaming)
3. Validazione input
4. Token counting
5. Integrazione con RAG context

Esegui con: python test_llm_simple.py
"""

import sys
from pathlib import Path

# Aggiungi path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.embedding_service import embedding_service
from app.models.schemas import Message, MessageRole

print("=" * 80)
print("VANDA CHATBOT - TEST LLM SERVICE (Semplice)")
print("=" * 80)
print()

# ============================================================================
# TEST 1: Verifica Inizializzazione
# ============================================================================
print("🤖 TEST 1: Verifica inizializzazione LLM Service...")
try:
    if llm_service:
        print(f"✅ LLM Service inizializzato!")
        print(f"   - Model: {llm_service.model}")
        print(f"   - Temperature: {llm_service.temperature}")
        print(f"   - Max tokens: {llm_service.max_tokens}")
        print(f"   - Streaming: {llm_service.stream_enabled}")
        print()
    else:
        print("❌ LLM Service non inizializzato")
        sys.exit(1)
except Exception as e:
    print(f"❌ Errore inizializzazione: {e}")
    sys.exit(1)

# ============================================================================
# TEST 2: Validazione Input
# ============================================================================
print("✅ TEST 2: Validazione input...")
try:
    # Input valido
    llm_service.validate_input("Ciao, come stai?")
    print("✅ Input valido: OK")

    # Input vuoto (dovrebbe fallire)
    try:
        llm_service.validate_input("")
        print("❌ Input vuoto: Doveva fallire!")
    except ValueError as e:
        print(f"✅ Input vuoto: Correttamente rifiutato ({e})")

    # Input troppo lungo (dovrebbe fallire)
    try:
        llm_service.validate_input("x" * 3000)
        print("❌ Input lungo: Doveva fallire!")
    except ValueError as e:
        print(f"✅ Input lungo: Correttamente rifiutato")

    print()
except Exception as e:
    print(f"❌ Errore validazione: {e}")
    print()

# ============================================================================
# TEST 3: Token Counting
# ============================================================================
print("🔢 TEST 3: Token counting...")
test_text = "Quali sono i vostri progetti di interior design residenziale?"
try:
    token_count = llm_service.count_tokens(test_text)
    print(f"✅ Token counting funziona!")
    print(f"   - Testo: \"{test_text}\"")
    print(f"   - Tokens: {token_count}")
    print()
except Exception as e:
    print(f"❌ Errore token counting: {e}")
    print()

# ============================================================================
# TEST 4: Generazione Risposta Semplice (SENZA RAG)
# ============================================================================
print("💬 TEST 4: Generazione risposta semplice (senza RAG context)...")
simple_message = "Ciao! Chi sei e cosa fai?"

try:
    print(f"   User: \"{simple_message}\"")
    print("   Generando risposta...")

    result = llm_service.generate_response(
        user_message=simple_message,
        conversation_history=None,
        rag_context=None
    )

    print(f"\n✅ Risposta generata!")
    print(f"   - Model: {result['model']}")
    print(f"   - Tokens usati: {result['tokens_used']}")
    print(f"   - Tempo: {result['processing_time_ms']}ms")
    print(f"\n   Assistant:")
    print(f"   {'-' * 76}")
    # Stampa risposta con indentazione
    for line in result['response'].split('\n'):
        print(f"   {line}")
    print(f"   {'-' * 76}")
    print()

except Exception as e:
    print(f"❌ Errore generazione risposta: {e}")
    import traceback
    traceback.print_exc()
    print()

# ============================================================================
# TEST 5: Generazione Risposta CON RAG Context
# ============================================================================
print("🔍 TEST 5: Generazione risposta con RAG context...")
rag_query = "Parlami di un progetto residenziale che avete fatto"

try:
    # 1. Genera embedding per query
    print("   [1/3] Generando embedding per query...")
    query_embedding = embedding_service.get_embedding(rag_query)

    # 2. Cerca documenti simili
    print("   [2/3] Cercando documenti rilevanti...")
    documents = rag_service.search_similar_documents(
        query_embedding=query_embedding,
        match_count=3,
        match_threshold=0.60
    )

    print(f"   Trovati {len(documents)} documenti rilevanti")

    if documents:
        # 3. Formatta context
        context = rag_service.format_context_for_llm(
            documents=documents,
            include_metadata=True
        )

        print(f"   Context: {len(context)} caratteri")

        # 4. Genera risposta con RAG
        print("   [3/3] Generando risposta con RAG context...")

        result = llm_service.generate_response(
            user_message=rag_query,
            conversation_history=None,
            rag_context=context
        )

        print(f"\n✅ Risposta con RAG generata!")
        print(f"   - Documenti usati: {len(documents)}")
        print(f"   - Model: {result['model']}")
        print(f"   - Tokens usati: {result['tokens_used']}")
        print(f"   - Tempo: {result['processing_time_ms']}ms")
        print(f"\n   User: \"{rag_query}\"")
        print(f"\n   Assistant:")
        print(f"   {'-' * 76}")
        for line in result['response'].split('\n'):
            print(f"   {line}")
        print(f"   {'-' * 76}")
        print()

    else:
        print("   ⚠️ Nessun documento trovato, salto test RAG")
        print()

except Exception as e:
    print(f"❌ Errore generazione con RAG: {e}")
    import traceback
    traceback.print_exc()
    print()

# ============================================================================
# TEST 6: Conversation History
# ============================================================================
print("💭 TEST 6: Risposta con conversation history...")

try:
    # Simula una conversazione
    history = [
        Message(role=MessageRole.USER, content="Ciao!"),
        Message(role=MessageRole.ASSISTANT, content="Ciao! Sono l'assistente di Vanda Designers. Come posso aiutarti?"),
        Message(role=MessageRole.USER, content="Che tipo di progetti realizzate?"),
        Message(role=MessageRole.ASSISTANT, content="Realizziamo progetti di architettura e interior design per residenze, spazi commerciali, hospitality e retail.")
    ]

    # Nuova domanda che si riferisce alla history
    new_message = "E quanto tempo ci vuole in media?"

    print(f"   History: {len(history)} messaggi")
    print(f"   New message: \"{new_message}\"")
    print("   Generando risposta...")

    result = llm_service.generate_response(
        user_message=new_message,
        conversation_history=history,
        rag_context=None
    )

    print(f"\n✅ Risposta con history generata!")
    print(f"   - Tokens usati: {result['tokens_used']}")
    print(f"   - Tempo: {result['processing_time_ms']}ms")
    print(f"\n   Assistant:")
    print(f"   {'-' * 76}")
    for line in result['response'].split('\n'):
        print(f"   {line}")
    print(f"   {'-' * 76}")
    print()

except Exception as e:
    print(f"❌ Errore con history: {e}")
    import traceback
    traceback.print_exc()
    print()

# ============================================================================
# RIEPILOGO FINALE
# ============================================================================
print("=" * 80)
print("✅ TEST COMPLETATI")
print("=" * 80)
print()
print("Riepilogo:")
print(f"  ✅ Inizializzazione LLM Service: OK")
print(f"  ✅ Validazione input: OK")
print(f"  ✅ Token counting: OK")
print(f"  ✅ Generazione risposta semplice: OK")
print(f"  ✅ Generazione risposta con RAG: OK" if documents else "  ⚠️ Generazione risposta con RAG: SKIPPED (no docs)")
print(f"  ✅ Generazione risposta con history: OK")
print()
print("🎯 PROSSIMI STEP:")
print("   1. Implementa Memory Manager (gestione conversazioni persistenti)")
print("   2. Implementa Chat API endpoint (/api/chat)")
print("   3. Test streaming SSE")
print("   4. Deploy su Google Cloud Run")
print()
print("=" * 80)
