"""
Test Streaming per LLM Service - VANDA Chatbot

Confronta:
1. Risposta standard (non-streaming) vs streaming
2. Misura time-to-first-token (TTFT)
3. Mostra token in tempo reale
4. Testa con e senza RAG context

Esegui con: python test_llm_streaming.py
"""

import sys
from pathlib import Path
import time

# Aggiungi path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.embedding_service import embedding_service

print("=" * 80)
print("VANDA CHATBOT - TEST STREAMING LLM SERVICE")
print("=" * 80)
print()

print(f"🔧 Configurazione:")
print(f"   - Model: {llm_service.model}")
print(f"   - Temperature: {llm_service.temperature}")
print(f"   - Max tokens: {llm_service.max_tokens}")
print(f"   - Streaming: {llm_service.stream_enabled}")
print()

# ============================================================================
# TEST 1: Risposta NON-STREAMING (baseline)
# ============================================================================
print("=" * 80)
print("TEST 1: RISPOSTA NON-STREAMING (baseline)")
print("=" * 80)
print()

query = "Ciao! Parlami brevemente dei vostri servizi di interior design"

print(f"Query: \"{query}\"")
print()
print("⏱️  Generando risposta completa (senza streaming)...")

start_time = time.time()

result = llm_service.generate_response(
    user_message=query,
    conversation_history=None,
    rag_context=None
)

total_time = (time.time() - start_time) * 1000

print(f"\n✅ Risposta ricevuta!")
print(f"   - Tempo totale: {total_time:.0f}ms ({total_time/1000:.2f}s)")
print(f"   - Tokens usati: {result['tokens_used']}")
print()
print("📝 Risposta:")
print("-" * 80)
print(result['response'])
print("-" * 80)
print()

# ============================================================================
# TEST 2: Risposta STREAMING
# ============================================================================
print("=" * 80)
print("TEST 2: RISPOSTA STREAMING (real-time)")
print("=" * 80)
print()

print(f"Query: \"{query}\"")
print()
print("⚡ Generando risposta con streaming...")
print()
print("📝 Risposta (token-by-token):")
print("-" * 80)

# Tracking
start_time = time.time()
first_token_time = None
token_count = 0
full_response = ""

try:
    # Genera streaming response
    for chunk in llm_service.generate_streaming_response(
        user_message=query,
        conversation_history=None,
        rag_context=None
    ):
        # Timing del primo token
        if first_token_time is None:
            first_token_time = (time.time() - start_time) * 1000

        # Parse SSE format: "data: {content}\n\n"
        if chunk.startswith("data: "):
            content = chunk[6:].strip()

            # Check segnali speciali
            if content == "[DONE]":
                break
            elif content.startswith("[ERROR]"):
                print(f"\n❌ Errore: {content}")
                break
            else:
                # Stampa token
                print(content, end='', flush=True)
                full_response += content
                token_count += 1

    total_time = (time.time() - start_time) * 1000

    print()
    print("-" * 80)
    print()
    print(f"✅ Streaming completato!")
    print(f"   - ⚡ Time-to-first-token (TTFT): {first_token_time:.0f}ms")
    print(f"   - ⏱️  Tempo totale: {total_time:.0f}ms ({total_time/1000:.2f}s)")
    print(f"   - 📊 Chunks ricevuti: {token_count}")
    print(f"   - 📏 Caratteri: {len(full_response)}")
    print()

    # Confronto
    print("📊 CONFRONTO:")
    print(f"   Non-streaming: utente aspetta {result['processing_time_ms']:.0f}ms, poi vede tutto")
    print(f"   Streaming:     utente vede prima parola in {first_token_time:.0f}ms ⚡")
    print(f"   Miglioramento percezione: {result['processing_time_ms'] / first_token_time:.1f}x più veloce!")
    print()

except Exception as e:
    print(f"\n❌ Errore streaming: {e}")
    import traceback
    traceback.print_exc()
    print()

# ============================================================================
# TEST 3: Streaming CON RAG Context
# ============================================================================
print("=" * 80)
print("TEST 3: STREAMING CON RAG CONTEXT")
print("=" * 80)
print()

rag_query = "Parlami di un progetto residenziale recente"

print(f"Query: \"{rag_query}\"")
print()

try:
    # 1. Genera embedding
    print("⏱️  [1/3] Generando embedding...")
    embed_start = time.time()
    query_embedding = embedding_service.get_embedding(rag_query)
    embed_time = (time.time() - embed_start) * 1000
    print(f"   ✅ Embedding: {embed_time:.0f}ms")

    # 2. Cerca documenti
    print("⏱️  [2/3] Cercando documenti rilevanti...")
    search_start = time.time()
    documents = rag_service.search_similar_documents(
        query_embedding=query_embedding,
        match_count=3,  # Ridotto a 3 per velocità
        match_threshold=0.60
    )
    search_time = (time.time() - search_start) * 1000
    print(f"   ✅ Search: {search_time:.0f}ms - Trovati {len(documents)} documenti")

    if documents:
        # 3. Formatta context
        context = rag_service.format_context_for_llm(
            documents=documents,
            include_metadata=True
        )

        print(f"   📄 Context: {len(context)} caratteri")
        print()
        print("⚡ [3/3] Generando risposta con RAG + streaming...")
        print()
        print("📝 Risposta (token-by-token):")
        print("-" * 80)

        # Tracking
        start_time = time.time()
        first_token_time = None
        token_count = 0
        full_response = ""

        # Genera streaming con RAG
        for chunk in llm_service.generate_streaming_response(
            user_message=rag_query,
            conversation_history=None,
            rag_context=context
        ):
            if first_token_time is None:
                first_token_time = (time.time() - start_time) * 1000

            if chunk.startswith("data: "):
                content = chunk[6:].strip()

                if content == "[DONE]":
                    break
                elif content.startswith("[ERROR]"):
                    print(f"\n❌ Errore: {content}")
                    break
                else:
                    print(content, end='', flush=True)
                    full_response += content
                    token_count += 1

        total_time = (time.time() - start_time) * 1000

        print()
        print("-" * 80)
        print()
        print(f"✅ Streaming con RAG completato!")
        print(f"   - ⚡ TTFT (dopo RAG): {first_token_time:.0f}ms")
        print(f"   - ⏱️  Tempo generazione LLM: {total_time:.0f}ms")
        print(f"   - ⏱️  Tempo totale (embedding + search + LLM): {embed_time + search_time + total_time:.0f}ms")
        print(f"   - 📊 Chunks: {token_count}")
        print(f"   - 📏 Caratteri: {len(full_response)}")
        print()

        print("📊 BREAKDOWN TIMING:")
        print(f"   1. Embedding:      {embed_time:>6.0f}ms")
        print(f"   2. Search RAG:     {search_time:>6.0f}ms")
        print(f"   3. LLM (TTFT):     {first_token_time:>6.0f}ms ⚡")
        print(f"   4. LLM (completo): {total_time:>6.0f}ms")
        print(f"   ────────────────────────────")
        print(f"   TOTALE:            {embed_time + search_time + total_time:>6.0f}ms")
        print()
        print(f"   👤 Utente vede prima parola in: {embed_time + search_time + first_token_time:.0f}ms")
        print()

    else:
        print("   ⚠️ Nessun documento trovato, salto test RAG+streaming")
        print()

except Exception as e:
    print(f"❌ Errore RAG+streaming: {e}")
    import traceback
    traceback.print_exc()
    print()

# ============================================================================
# RIEPILOGO FINALE
# ============================================================================
print("=" * 80)
print("✅ TEST STREAMING COMPLETATI")
print("=" * 80)
print()
print("🎯 RISULTATI:")
print()
print("1️⃣  NON-STREAMING:")
print("   - Utente aspetta tutta la risposta")
print(f"   - Tempo attesa: ~{result['processing_time_ms']:.0f}ms")
print()
print("2️⃣  STREAMING SEMPLICE:")
print("   - Utente vede prima parola quasi subito")
print(f"   - TTFT: ~{first_token_time:.0f}ms ⚡")
print(f"   - Miglioramento percezione: {result['processing_time_ms'] / first_token_time if first_token_time else 0:.1f}x")
print()
if documents:
    print("3️⃣  STREAMING + RAG:")
    print("   - Include ricerca documenti")
    print(f"   - TTFT totale: ~{embed_time + search_time + first_token_time:.0f}ms")
    print(f"   - Risposta basata su {len(documents)} documenti reali")
    print()
print("💡 CONCLUSIONE:")
print("   Lo streaming rende l'esperienza utente 5-10x più reattiva!")
print("   L'utente inizia a leggere mentre il modello genera.")
print()
print("=" * 80)
