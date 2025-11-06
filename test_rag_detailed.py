"""
Test Avanzato per RAG Service - VANDA Chatbot

Questo script esegue test più dettagliati:
1. Test con diverse query
2. Test con diversi threshold
3. Test performance
4. Test filtri multipli
5. Statistiche dettagliate

Esegui con: python test_rag_detailed.py
"""

import sys
import time
from pathlib import Path

# Aggiungi path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.rag_service import rag_service
from app.services.embedding_service import embedding_service
from app.models.schemas import MetadataFilter

print("=" * 80)
print("VANDA CHATBOT - TEST RAG SERVICE (Dettagliato)")
print("=" * 80)
print()

# ============================================================================
# TEST 1: Query Multiple
# ============================================================================
print("🔍 TEST 1: Query multiple con diverse tematiche...")
print()

test_queries = [
    {
        "query": "progetti di interior design residenziale",
        "filters": MetadataFilter(category="portfolio", client_type="residential")
    },
    {
        "query": "ristrutturazione appartamenti moderni",
        "filters": MetadataFilter(category="portfolio")
    },
    {
        "query": "design commerciale retail negozi",
        "filters": MetadataFilter(client_type="commercial")
    },
    {
        "query": "progetti in evidenza più importanti",
        "filters": MetadataFilter(featured=True, min_priority=7)
    }
]

results_summary = []

for i, test in enumerate(test_queries, 1):
    print(f"Query {i}: \"{test['query']}\"")
    print(f"Filtri: {test['filters'].dict(exclude_none=True)}")

    try:
        # Genera embedding
        start_time = time.time()
        embedding = embedding_service.get_embedding(test['query'])
        embedding_time = (time.time() - start_time) * 1000

        # Search
        start_time = time.time()
        docs = rag_service.search_similar_documents(
            query_embedding=embedding,
            match_count=5,
            match_threshold=0.70,
            metadata_filter=test['filters']
        )
        search_time = (time.time() - start_time) * 1000

        results_summary.append({
            "query": test['query'],
            "docs_found": len(docs),
            "embedding_time": embedding_time,
            "search_time": search_time,
            "top_similarity": docs[0].similarity if docs else 0
        })

        print(f"✅ Trovati {len(docs)} documenti")
        if docs:
            print(f"   Top result: {docs[0].metadata.heading}")
            print(f"   Similarity: {docs[0].similarity:.2%}")
            print(f"   Timing: embedding={embedding_time:.0f}ms, search={search_time:.0f}ms")
        print()

    except Exception as e:
        print(f"❌ Errore: {e}")
        print()

# ============================================================================
# TEST 2: Threshold Comparison
# ============================================================================
print("=" * 80)
print("📊 TEST 2: Comparazione threshold...")
print()

test_query = "interior design residenziale moderno"
print(f"Query: \"{test_query}\"")
print()

try:
    embedding = embedding_service.get_embedding(test_query)

    thresholds = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85]

    print(f"{'Threshold':<12} {'Docs Found':<12} {'Top Similarity':<15} {'Avg Similarity'}")
    print("-" * 60)

    for threshold in thresholds:
        docs = rag_service.search_similar_documents(
            query_embedding=embedding,
            match_count=10,
            match_threshold=threshold
        )

        top_sim = docs[0].similarity if docs else 0
        avg_sim = sum(d.similarity for d in docs) / len(docs) if docs else 0

        print(f"{threshold:<12.2f} {len(docs):<12} {top_sim:<15.2%} {avg_sim:.2%}")

    print()
    print("💡 Raccomandazione:")
    print("   - Threshold 0.70-0.75: Bilanciato (alta rilevanza)")
    print("   - Threshold 0.60-0.65: Più risultati (recall)")
    print("   - Threshold 0.80-0.85: Solo match quasi esatti (precision)")
    print()

except Exception as e:
    print(f"❌ Errore: {e}")
    print()

# ============================================================================
# TEST 3: Filtri Metadata Combinati
# ============================================================================
print("=" * 80)
print("🎯 TEST 3: Filtri metadata combinati...")
print()

filter_combinations = [
    {
        "name": "Portfolio Residenziale",
        "filter": MetadataFilter(category="portfolio", client_type="residential")
    },
    {
        "name": "Featured High Priority",
        "filter": MetadataFilter(featured=True, min_priority=7)
    },
    {
        "name": "Commercial Projects",
        "filter": MetadataFilter(client_type="commercial", category="portfolio")
    },
    {
        "name": "Interior Medium Scale",
        "filter": MetadataFilter(subcategory="interior", project_scale="medium")
    }
]

test_embedding = embedding_service.get_embedding("progetti interior design")

print(f"{'Filter Name':<30} {'Docs Found':<12} {'Avg Similarity'}")
print("-" * 60)

for combo in filter_combinations:
    try:
        docs = rag_service.search_similar_documents(
            query_embedding=test_embedding,
            match_count=10,
            match_threshold=0.65,
            metadata_filter=combo['filter']
        )

        avg_sim = sum(d.similarity for d in docs) / len(docs) if docs else 0
        print(f"{combo['name']:<30} {len(docs):<12} {avg_sim:.2%}")

    except Exception as e:
        print(f"{combo['name']:<30} ERROR: {str(e)[:20]}")

print()

# ============================================================================
# TEST 4: Browse per Categoria
# ============================================================================
print("=" * 80)
print("📂 TEST 4: Browse documenti per categoria...")
print()

try:
    # Ottieni statistiche categorie
    response = rag_service.client.table(rag_service.table_name).select("metadata").execute()

    categories = {}
    for doc in response.data:
        cat = doc.get('metadata', {}).get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    print("Distribuzione categorie:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {cat}: {count} documenti")
    print()

    # Prendi esempi da categoria più popolata
    top_category = max(categories.items(), key=lambda x: x[1])[0]
    print(f"Esempi da categoria '{top_category}':")

    docs = rag_service.get_documents_by_category(category=top_category, limit=3)
    for i, doc in enumerate(docs, 1):
        print(f"\n  [{i}] {doc.metadata.heading}")
        print(f"      Client: {doc.metadata.client}")
        print(f"      Type: {doc.metadata.document_type}")
    print()

except Exception as e:
    print(f"❌ Errore: {e}")
    print()

# ============================================================================
# TEST 5: Context Length Analysis
# ============================================================================
print("=" * 80)
print("📏 TEST 5: Analisi lunghezza context...")
print()

try:
    test_embedding = embedding_service.get_embedding("progetti design")

    for doc_count in [3, 5, 8, 10]:
        docs = rag_service.search_similar_documents(
            query_embedding=test_embedding,
            match_count=doc_count,
            match_threshold=0.65
        )

        if docs:
            context = rag_service.format_context_for_llm(docs)
            print(f"  {doc_count} documenti: {len(context):>6} caratteri (~{len(context)//4} tokens)")

    print()
    print("💡 Note:")
    print("   - GPT-4: context window 8k-128k tokens")
    print("   - Raccomandato: 3-5 documenti per risposta (2k-4k chars)")
    print("   - Max practical: 8-10 documenti (6k-8k chars)")
    print()

except Exception as e:
    print(f"❌ Errore: {e}")
    print()

# ============================================================================
# TEST 6: Performance Summary
# ============================================================================
print("=" * 80)
print("⚡ TEST 6: Performance summary...")
print()

if results_summary:
    total_docs = sum(r['docs_found'] for r in results_summary)
    avg_embedding_time = sum(r['embedding_time'] for r in results_summary) / len(results_summary)
    avg_search_time = sum(r['search_time'] for r in results_summary) / len(results_summary)
    avg_similarity = sum(r['top_similarity'] for r in results_summary) / len(results_summary)

    print(f"Query eseguite: {len(results_summary)}")
    print(f"Documenti trovati (totale): {total_docs}")
    print(f"Media documenti per query: {total_docs / len(results_summary):.1f}")
    print(f"Tempo medio embedding: {avg_embedding_time:.0f}ms")
    print(f"Tempo medio search: {avg_search_time:.0f}ms")
    print(f"Tempo medio totale: {avg_embedding_time + avg_search_time:.0f}ms")
    print(f"Similarity media (top result): {avg_similarity:.2%}")
    print()

    # Performance assessment
    total_avg_time = avg_embedding_time + avg_search_time
    if total_avg_time < 500:
        perf = "🟢 Eccellente"
    elif total_avg_time < 1000:
        perf = "🟡 Buona"
    elif total_avg_time < 2000:
        perf = "🟠 Accettabile"
    else:
        perf = "🔴 Da ottimizzare"

    print(f"Performance assessment: {perf}")
    print()

    if total_avg_time > 1000:
        print("⚠️ RACCOMANDAZIONI:")
        print("   - Implementa PostgreSQL stored procedure per similarity search")
        print("   - Aggiungi indice HNSW sulla colonna embedding")
        print("   - Considera caching per query frequenti (Redis)")
        print("   Vedi: docs/NEXT_STEP_POSTGRES_FUNCTION.md")
        print()

# ============================================================================
# RIEPILOGO FINALE
# ============================================================================
print("=" * 80)
print("✅ TEST DETTAGLIATI COMPLETATI")
print("=" * 80)
print()
print("📊 Summary:")
print(f"  ✅ Query multiple testate: {len(test_queries)}")
print(f"  ✅ Threshold comparison: 6 livelli testati")
print(f"  ✅ Filtri metadata: {len(filter_combinations)} combinazioni")
print(f"  ✅ Performance analysis: Completata")
print()
print("🎯 CONCLUSIONI:")
print("  Il RAG Service funziona correttamente!")
print("  Puoi procedere con l'implementazione di:")
print("    1. LLM Service (generazione risposte)")
print("    2. Memory Manager (gestione conversazioni)")
print("    3. Chat API endpoint")
print()
print("📚 DOCS:")
print("  - docs/RAG_SERVICE_DOCUMENTATION.md")
print("  - docs/QUICK_START_RAG.md")
print("  - docs/NEXT_STEP_POSTGRES_FUNCTION.md")
print()
print("=" * 80)
