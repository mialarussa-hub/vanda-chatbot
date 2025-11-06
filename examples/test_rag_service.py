"""
Esempio di utilizzo del RAGService per VANDA chatbot.

Questo script dimostra come:
1. Inizializzare il RAG service
2. Creare embedding di una query
3. Eseguire similarity search con filtri
4. Formattare il context per LLM
"""

import sys
import os

# Aggiungi parent directory al path per importare i moduli
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.rag_service import RAGService
from app.services.embedding_service import EmbeddingService
from app.models.schemas import MetadataFilter
from loguru import logger

# Configura logging
logger.add(
    "test_rag.log",
    rotation="1 MB",
    level="DEBUG"
)


def test_basic_search():
    """Test base di similarity search senza filtri"""
    print("\n" + "="*80)
    print("TEST 1: BASIC SIMILARITY SEARCH")
    print("="*80 + "\n")

    # Inizializza servizi
    rag = RAGService()
    embedding_service = EmbeddingService()

    # Query utente
    query = "Progetti di interior design residenziale moderni"
    print(f"Query: {query}\n")

    # Genera embedding
    print("Generating embedding...")
    query_embedding = embedding_service.get_embedding(query)
    print(f"Embedding dimension: {len(query_embedding)}\n")

    # Cerca documenti simili
    print("Searching similar documents...")
    documents = rag.search_similar_documents(
        query_embedding=query_embedding,
        match_count=3,
        match_threshold=0.70
    )

    # Mostra risultati
    print(f"\nFound {len(documents)} relevant documents:\n")

    for i, doc in enumerate(documents, 1):
        print(f"--- Document {i} ---")
        print(f"ID: {doc.id}")
        print(f"Similarity: {doc.similarity:.4f}")
        print(f"Heading: {doc.metadata.heading or 'N/A'}")
        print(f"Category: {doc.metadata.category or 'N/A'}")
        print(f"Client Type: {doc.metadata.client_type or 'N/A'}")
        print(f"Content Preview: {doc.content[:200]}...")
        print()


def test_filtered_search():
    """Test di similarity search con filtri metadata"""
    print("\n" + "="*80)
    print("TEST 2: FILTERED SIMILARITY SEARCH")
    print("="*80 + "\n")

    rag = RAGService()
    embedding_service = EmbeddingService()

    # Query utente
    query = "Progetti di interior design"
    print(f"Query: {query}")

    # Definisci filtri
    filters = MetadataFilter(
        category="portfolio",
        client_type="residential",
        featured=True,
        min_priority=5
    )

    print(f"Filters:")
    print(f"  - category: {filters.category}")
    print(f"  - client_type: {filters.client_type}")
    print(f"  - featured: {filters.featured}")
    print(f"  - min_priority: {filters.min_priority}\n")

    # Genera embedding
    query_embedding = embedding_service.get_embedding(query)

    # Cerca con filtri
    print("Searching with filters...")
    documents = rag.search_similar_documents(
        query_embedding=query_embedding,
        match_count=5,
        match_threshold=0.70,
        metadata_filter=filters
    )

    # Mostra risultati
    print(f"\nFound {len(documents)} relevant documents:\n")

    for i, doc in enumerate(documents, 1):
        print(f"--- Document {i} ---")
        print(f"ID: {doc.id}")
        print(f"Similarity: {doc.similarity:.4f}")
        print(f"Heading: {doc.metadata.heading or 'N/A'}")
        print(f"Featured: {doc.metadata.featured}")
        print(f"Priority: {doc.metadata.priority}")
        print()


def test_context_formatting():
    """Test formattazione context per LLM"""
    print("\n" + "="*80)
    print("TEST 3: CONTEXT FORMATTING FOR LLM")
    print("="*80 + "\n")

    rag = RAGService()
    embedding_service = EmbeddingService()

    # Query
    query = "Progetti retail e commerciali"
    print(f"Query: {query}\n")

    # Genera embedding e cerca
    query_embedding = embedding_service.get_embedding(query)

    filters = MetadataFilter(
        client_type="retail"
    )

    documents = rag.search_similar_documents(
        query_embedding=query_embedding,
        match_count=3,
        match_threshold=0.65,
        metadata_filter=filters
    )

    # Formatta context
    print(f"Found {len(documents)} documents, formatting context...\n")

    context = rag.format_context_for_llm(
        documents=documents,
        include_metadata=True,
        max_context_length=2000  # Limite per l'esempio
    )

    print("FORMATTED CONTEXT:")
    print("-" * 80)
    print(context)
    print("-" * 80)
    print(f"\nContext length: {len(context)} characters")


def test_get_by_id():
    """Test recupero documento per ID"""
    print("\n" + "="*80)
    print("TEST 4: GET DOCUMENT BY ID")
    print("="*80 + "\n")

    rag = RAGService()

    # Recupera documento con ID 1 (se esiste)
    doc_id = 1
    print(f"Fetching document ID: {doc_id}\n")

    document = rag.get_document_by_id(doc_id)

    if document:
        print("Document found!")
        print(f"ID: {document.id}")
        print(f"Heading: {document.metadata.heading or 'N/A'}")
        print(f"Category: {document.metadata.category or 'N/A'}")
        print(f"URL: {document.metadata.url or 'N/A'}")
        print(f"Content length: {len(document.content)} chars")
        print(f"\nContent preview:\n{document.content[:300]}...")
    else:
        print(f"Document {doc_id} not found")


def test_get_by_category():
    """Test recupero documenti per categoria"""
    print("\n" + "="*80)
    print("TEST 5: GET DOCUMENTS BY CATEGORY")
    print("="*80 + "\n")

    rag = RAGService()

    category = "portfolio"
    limit = 5

    print(f"Fetching documents - Category: {category}, Limit: {limit}\n")

    documents = rag.get_documents_by_category(
        category=category,
        limit=limit
    )

    print(f"Found {len(documents)} documents:\n")

    for i, doc in enumerate(documents, 1):
        print(f"{i}. {doc.metadata.heading or 'Untitled'} (ID: {doc.id})")


def test_database_stats():
    """Test statistiche database"""
    print("\n" + "="*80)
    print("TEST 6: DATABASE STATISTICS")
    print("="*80 + "\n")

    rag = RAGService()

    stats = rag.get_database_stats()

    print("Database Statistics:")
    print(f"  - Total documents: {stats.get('total_documents', 0)}")
    print(f"  - Table name: {stats.get('table_name', 'N/A')}")
    print(f"  - Embedding dimension: {stats.get('embedding_dimension', 0)}")
    print(f"  - Status: {stats.get('status', 'unknown')}")


def main():
    """Esegui tutti i test"""
    print("\n")
    print("#" * 80)
    print("# VANDA CHATBOT - RAG SERVICE TEST SUITE")
    print("#" * 80)

    try:
        # Esegui i test in sequenza
        test_basic_search()
        test_filtered_search()
        test_context_formatting()
        test_get_by_id()
        test_get_by_category()
        test_database_stats()

        print("\n" + "="*80)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
