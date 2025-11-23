import sys
import os
import asyncio
from typing import List

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.config import settings

async def test_hybrid_search():
    print("=" * 80)
    print("TEST RICERCA IBRIDA (Hybrid Search)")
    print("=" * 80)

    rag = RAGService()
    llm = LLMService()

    # Test cases: query che beneficiano della ricerca per parole chiave
    queries = [
        "Progetto Campana",      # Nome specifico
        "Codice 123",            # Codice/Numero (ipotetico)
        "Interior design",       # Concetto generico
    ]

    # Setup OpenAI client for embeddings
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    for query_text in queries:
        print(f"\n🔎 Query: '{query_text}'")
        
        # 1. Genera embedding
        emb_response = await openai_client.embeddings.create(
            input=query_text,
            model="text-embedding-3-small" # O quello che usa il progetto
        )
        embedding = emb_response.data[0].embedding
        
        # 2. Cerca
        results = rag.search_similar_documents(
            query_embedding=embedding,
            query_text=query_text,
            match_count=3
        )

        if not results:
            print("   ❌ Nessun risultato trovato.")
            continue

        for i, doc in enumerate(results, 1):
            heading = doc.metadata.heading if doc.metadata else "No Title"
            snippet = doc.content[:100].replace('\n', ' ') + "..."
            score = doc.similarity
            print(f"   {i}. [{score:.4f}] {heading}")
            print(f"      {snippet}")

    print("\n" + "=" * 80)
    print("Test completato.")

if __name__ == "__main__":
    asyncio.run(test_hybrid_search())
