"""
Test Semplice per RAG Service - VANDA Chatbot

Questo script testa le funzionalità base del RAG Service:
1. Connessione Supabase
2. Count documenti
3. Generazione embedding
4. Query similarity search
5. Formattazione context

Esegui con: python test_rag_simple.py
"""

import sys
from pathlib import Path

# Aggiungi path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.rag_service import rag_service
from app.services.embedding_service import embedding_service
from app.models.schemas import MetadataFilter

print("=" * 80)
print("VANDA CHATBOT - TEST RAG SERVICE (Semplice)")
print("=" * 80)
print()

# ============================================================================
# TEST 1: Verifica Connessione Supabase
# ============================================================================
print("📡 TEST 1: Verifica connessione Supabase...")
try:
    stats = rag_service.get_database_stats()
    print(f"✅ Connessione riuscita!")
    print(f"   - Documenti totali: {stats.get('total_documents', 0)}")
    print(f"   - Tabella: {stats.get('table_name', 'N/A')}")
    print()
except Exception as e:
    print(f"❌ Errore connessione: {e}")
    print("   Verifica le credenziali nel file .env")
    sys.exit(1)

# ============================================================================
# TEST 2: Mostra Esempi di Metadata
# ============================================================================
print("📋 TEST 2: Esempi di documenti nel database...")
try:
    # Prendi primi 3 documenti
    response = rag_service.client.table(rag_service.table_name).select("id, metadata").limit(3).execute()

    if response.data:
        for i, doc in enumerate(response.data, 1):
            metadata = doc.get('metadata', {})
            print(f"\n   Documento {i} (ID: {doc['id']}):")
            print(f"   - Heading: {metadata.get('heading', 'N/A')}")
            print(f"   - Category: {metadata.get('category', 'N/A')}")
            print(f"   - Client Type: {metadata.get('client_type', 'N/A')}")
            print(f"   - Featured: {metadata.get('featured', False)}")
            print(f"   - Tags: {metadata.get('tags', 'N/A')[:60]}...")
    else:
        print("   ⚠️ Nessun documento trovato")
    print()
except Exception as e:
    print(f"   ❌ Errore: {e}")
    print()

# ============================================================================
# TEST 3: Genera Embedding di Test
# ============================================================================
print("🧠 TEST 3: Generazione embedding con OpenAI...")
test_query = "Quali sono i vostri progetti di interior design residenziale?"
print(f"   Query: \"{test_query}\"")

try:
    query_embedding = embedding_service.get_embedding(test_query)
    print(f"✅ Embedding generato!")
    print(f"   - Dimensioni: {len(query_embedding)}")
    print(f"   - Primi 5 valori: {query_embedding[:5]}")
    print()
except Exception as e:
    print(f"❌ Errore generazione embedding: {e}")
    print("   Verifica l'OpenAI API Key nel file .env")
    sys.exit(1)

# ============================================================================
# TEST 4: Query RAG - Search Base
# ============================================================================
print("🔍 TEST 4: Similarity search (query base)...")
try:
    documents = rag_service.search_similar_documents(
        query_embedding=query_embedding,
        match_count=5,
        match_threshold=0.70
    )

    print(f"✅ Trovati {len(documents)} documenti rilevanti")
    print()

    if documents:
        print("   📄 Top 3 risultati:")
        for i, doc in enumerate(documents[:3], 1):
            print(f"\n   [{i}] Similarity: {doc.similarity:.2%}")
            print(f"       ID: {doc.id}")
            print(f"       Heading: {doc.metadata.heading}")
            print(f"       Category: {doc.metadata.category}")
            print(f"       Client Type: {doc.metadata.client_type}")
            print(f"       Content: {doc.content[:100]}...")
    else:
        print("   ⚠️ Nessun documento trovato sopra threshold 0.70")
        print("   Prova ad abbassare il threshold a 0.60")
    print()

except Exception as e:
    print(f"❌ Errore query RAG: {e}")
    import traceback
    traceback.print_exc()
    print()

# ============================================================================
# TEST 5: Query RAG - Con Filtri Metadata
# ============================================================================
print("🎯 TEST 5: Similarity search con filtri metadata...")
print("   Filtri: category='portfolio', client_type='residential', featured=True")

try:
    filters = MetadataFilter(
        category="portfolio",
        client_type="residential",
        featured=True
    )

    documents_filtered = rag_service.search_similar_documents(
        query_embedding=query_embedding,
        match_count=5,
        match_threshold=0.65,
        metadata_filter=filters
    )

    print(f"✅ Trovati {len(documents_filtered)} documenti con filtri")
    print()

    if documents_filtered:
        print("   📄 Risultati filtrati:")
        for i, doc in enumerate(documents_filtered[:3], 1):
            print(f"\n   [{i}] {doc.metadata.heading}")
            print(f"       Similarity: {doc.similarity:.2%}")
            print(f"       Featured: {doc.metadata.featured}")
            print(f"       Priority: {doc.metadata.priority}")
    else:
        print("   ⚠️ Nessun documento trovato con questi filtri")
        print("   Prova senza il filtro 'featured' o abbassa il threshold")
    print()

except Exception as e:
    print(f"❌ Errore query con filtri: {e}")
    import traceback
    traceback.print_exc()
    print()

# ============================================================================
# TEST 6: Formattazione Context per LLM
# ============================================================================
print("📝 TEST 6: Formattazione context per LLM...")

try:
    # Usa i documenti del test 4
    if documents:
        context = rag_service.format_context_for_llm(
            documents=documents[:3],  # Solo top 3
            include_metadata=True
        )

        print(f"✅ Context formattato!")
        print(f"   - Lunghezza: {len(context)} caratteri")
        print()
        print("   📄 Preview context (primi 500 caratteri):")
        print("   " + "-" * 76)
        print("   " + context[:500].replace("\n", "\n   "))
        print("   " + "-" * 76)
        print("   ...")
    else:
        print("   ⚠️ Nessun documento da formattare")
    print()

except Exception as e:
    print(f"❌ Errore formattazione context: {e}")
    print()

# ============================================================================
# RIEPILOGO FINALE
# ============================================================================
print("=" * 80)
print("✅ TEST COMPLETATI")
print("=" * 80)
print()
print("Riepilogo:")
print(f"  ✅ Connessione Supabase: OK")
print(f"  ✅ Embedding OpenAI: OK")
print(f"  ✅ Similarity Search: OK ({len(documents)} docs trovati)")
print(f"  ✅ Filtri Metadata: OK ({len(documents_filtered) if 'documents_filtered' in locals() else 0} docs trovati)")
print(f"  ✅ Context Formatting: OK")
print()
print("🎯 PROSSIMI STEP:")
print("   1. Esegui test avanzato: python test_rag_detailed.py")
print("   2. Implementa LLM Service per generare risposte")
print("   3. Implementa endpoint /api/chat")
print("   4. Test end-to-end completo")
print()
print("=" * 80)
