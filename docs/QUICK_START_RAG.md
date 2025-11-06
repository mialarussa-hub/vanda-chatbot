# Quick Start Guide - RAG Service

Guida rapida per iniziare ad usare il RAGService nel progetto VANDA chatbot.

---

## 1. Setup Environment

### Installa Dependencies

```bash
cd D:\PROGETTI\AGENTIKA\WEB\vanda-chatbot
pip install -r requirements.txt
```

### Configura .env

Crea un file `.env` nella root del progetto:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJ...your-service-role-key
SUPABASE_TABLE_NAME=documents

# OpenAI
OPENAI_API_KEY=sk-...your-api-key

# App Config
LOG_LEVEL=INFO
ENV=development
```

---

## 2. Esempio Base - Similarity Search

```python
from app.services.rag_service import rag_service
from app.services.embedding_service import embedding_service

# 1. Definisci la query utente
user_query = "Progetti di interior design moderni"

# 2. Genera embedding della query
query_embedding = embedding_service.get_embedding(user_query)

# 3. Cerca documenti simili
documents = rag_service.search_similar_documents(
    query_embedding=query_embedding,
    match_count=5,           # Top-5 risultati
    match_threshold=0.75     # Solo similarity >= 0.75
)

# 4. Mostra risultati
print(f"Trovati {len(documents)} documenti rilevanti:\n")

for i, doc in enumerate(documents, 1):
    print(f"--- Documento {i} ---")
    print(f"Similarity: {doc.similarity:.4f}")
    print(f"Titolo: {doc.metadata.heading}")
    print(f"Categoria: {doc.metadata.category}")
    print(f"Preview: {doc.content[:150]}...\n")
```

---

## 3. Esempio con Filtri Metadata

```python
from app.models.schemas import MetadataFilter

# Definisci filtri specifici
filters = MetadataFilter(
    category="portfolio",        # Solo progetti portfolio
    client_type="residential",   # Solo clienti residenziali
    featured=True,               # Solo progetti in evidenza
    min_priority=5               # Priorità >= 5
)

# Cerca con filtri applicati
documents = rag_service.search_similar_documents(
    query_embedding=query_embedding,
    match_count=3,
    match_threshold=0.70,
    metadata_filter=filters      # Applica filtri
)

print(f"Documenti trovati con filtri: {len(documents)}")
```

---

## 4. Formattare Context per LLM

```python
# Dopo aver recuperato i documenti con similarity search...

# Formatta in context string per il LLM
context = rag_service.format_context_for_llm(
    documents=documents,
    include_metadata=True,        # Include titolo, categoria, tags
    max_context_length=8000       # Limit per token budget
)

# Il context è pronto per essere usato nel prompt
print("Context formattato:")
print(context)

# Esempio: usa il context con OpenAI
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": f"""Sei un assistente esperto di Vanda Designers.
Rispondi usando le seguenti informazioni dal database:

{context}
"""
        },
        {
            "role": "user",
            "content": user_query
        }
    ],
    temperature=0.7,
    max_tokens=800
)

print(response.choices[0].message.content)
```

---

## 5. Recuperare Documento Specifico

```python
# Recupera un documento per ID
doc_id = 123
document = rag_service.get_document_by_id(doc_id)

if document:
    print(f"Documento #{doc_id}:")
    print(f"Titolo: {document.metadata.heading}")
    print(f"URL: {document.metadata.url}")
    print(f"Content: {document.content[:200]}...")
else:
    print(f"Documento {doc_id} non trovato")
```

---

## 6. Browse per Categoria

```python
# Ottieni tutti i documenti di una categoria
category = "portfolio"
documents = rag_service.get_documents_by_category(
    category=category,
    limit=10
)

print(f"Documenti in categoria '{category}':\n")
for doc in documents:
    print(f"- {doc.metadata.heading} (ID: {doc.id})")
```

---

## 7. Statistiche Database

```python
# Ottieni info sul database
stats = rag_service.get_database_stats()

print("Database Statistics:")
print(f"  Total documents: {stats['total_documents']}")
print(f"  Table name: {stats['table_name']}")
print(f"  Embedding dimension: {stats['embedding_dimension']}")
print(f"  Status: {stats['status']}")
```

---

## 8. Esempio Completo - RAG Pipeline

```python
from app.services.rag_service import rag_service
from app.services.embedding_service import embedding_service
from app.models.schemas import MetadataFilter
from openai import OpenAI

def rag_query(user_query: str, filters: MetadataFilter = None):
    """
    Pipeline RAG completa:
    1. Embedding della query
    2. Similarity search con filtri
    3. Formattazione context
    4. Generazione risposta LLM
    """

    print(f"Query: {user_query}\n")

    # Step 1: Embedding
    print("1. Generating embedding...")
    query_embedding = embedding_service.get_embedding(user_query)

    # Step 2: Similarity Search
    print("2. Searching similar documents...")
    documents = rag_service.search_similar_documents(
        query_embedding=query_embedding,
        match_count=5,
        match_threshold=0.75,
        metadata_filter=filters
    )

    if not documents:
        return "Non ho trovato documenti rilevanti per la tua domanda."

    print(f"   Found {len(documents)} relevant documents")

    # Step 3: Format Context
    print("3. Formatting context...")
    context = rag_service.format_context_for_llm(
        documents=documents,
        include_metadata=True,
        max_context_length=8000
    )

    # Step 4: Generate Response
    print("4. Generating LLM response...\n")

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": f"""Sei un assistente esperto di Vanda Designers,
studio di architettura e design d'interni.

Usa le seguenti informazioni per rispondere alla domanda dell'utente:

{context}

ISTRUZIONI:
- Rispondi in modo professionale e dettagliato
- Cita specificamente i progetti quando pertinenti
- Se le informazioni non sono sufficienti, dillo chiaramente
- Mantieni un tono friendly ma professionale
"""
            },
            {
                "role": "user",
                "content": user_query
            }
        ],
        temperature=0.7,
        max_tokens=800
    )

    answer = response.choices[0].message.content

    # Return answer + sources
    return {
        "answer": answer,
        "sources": [
            {
                "id": doc.id,
                "heading": doc.metadata.heading,
                "similarity": doc.similarity,
                "url": doc.metadata.url
            }
            for doc in documents
        ]
    }


# ESEMPIO D'USO

# Query semplice
result = rag_query("Quali sono i vostri progetti più innovativi?")
print(result["answer"])
print("\nFonti utilizzate:")
for source in result["sources"]:
    print(f"  - {source['heading']} (similarity: {source['similarity']:.2%})")

# Query con filtri
filters = MetadataFilter(
    category="portfolio",
    client_type="residential",
    featured=True
)

result = rag_query(
    "Parlami dei vostri progetti residenziali in evidenza",
    filters=filters
)
print(result["answer"])
```

---

## 9. Best Practices

### Threshold Selection

```python
# Alta precisione - Solo risultati molto rilevanti
documents = rag_service.search_similar_documents(
    query_embedding=embedding,
    match_threshold=0.85,
    match_count=3
)

# Bilanciato (default) - Buon balance
documents = rag_service.search_similar_documents(
    query_embedding=embedding,
    match_threshold=0.75,  # RECOMMENDED
    match_count=5
)

# Alta recall - Più risultati
documents = rag_service.search_similar_documents(
    query_embedding=embedding,
    match_threshold=0.65,
    match_count=10
)
```

### Error Handling

```python
from loguru import logger

try:
    # Genera embedding
    query_embedding = embedding_service.get_embedding(user_query)

    # Cerca documenti
    documents = rag_service.search_similar_documents(
        query_embedding=query_embedding,
        match_count=5,
        match_threshold=0.75
    )

    if not documents:
        logger.warning(f"No documents found for query: {user_query}")
        return "Non ho trovato informazioni rilevanti."

    # Procedi con la generazione...

except ValueError as e:
    logger.error(f"Validation error: {e}")
    return "Errore nella validazione dei dati."

except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return "Si è verificato un errore. Riprova più tardi."
```

### Filtri Comuni

```python
# Solo progetti portfolio
MetadataFilter(category="portfolio")

# Solo progetti residenziali in evidenza
MetadataFilter(
    client_type="residential",
    featured=True
)

# Solo progetti retail/commercial ad alta priorità
MetadataFilter(
    client_type="retail",
    min_priority=7
)

# Progetti large scale in portfolio
MetadataFilter(
    category="portfolio",
    project_scale="large"
)
```

---

## 10. Testing

### Run Test Suite

```bash
# Assicurati di essere nella directory del progetto
cd D:\PROGETTI\AGENTIKA\WEB\vanda-chatbot

# Run test suite
python examples/test_rag_service.py
```

### Test Singoli

```python
# Test 1: Basic search
from examples.test_rag_service import test_basic_search
test_basic_search()

# Test 2: Filtered search
from examples.test_rag_service import test_filtered_search
test_filtered_search()

# Test 3: Context formatting
from examples.test_rag_service import test_context_formatting
test_context_formatting()
```

---

## Troubleshooting

### Problema: Nessun risultato trovato

**Soluzione:**
1. Verifica che il database contenga documenti
2. Abbassa il threshold (es: 0.65)
3. Rimuovi i filtri metadata
4. Controlla che l'embedding sia corretto (1536 dimensioni)

### Problema: Risultati poco rilevanti

**Soluzione:**
1. Aumenta il threshold (es: 0.80)
2. Riformula la query con keywords più specifiche
3. Usa filtri metadata per raffinare
4. Riduci match_count per avere solo i top risultati

### Problema: Errore "Expected 1536 dimensions"

**Soluzione:**
- Assicurati di usare `text-embedding-3-small`
- Verifica che il vettore non sia corrotto

---

## Next Steps

1. **Implementa l'endpoint chat API** usando il RAGService
2. **Aggiungi streaming** per risposte in tempo reale
3. **Implementa memory/conversation history**
4. **Ottimizza con stored procedure** PostgreSQL
5. **Aggiungi caching** (Redis) per query frequenti

---

## Resources

- **Documentazione completa**: `docs/RAG_SERVICE_DOCUMENTATION.md`
- **Test suite**: `examples/test_rag_service.py`
- **Schema Pydantic**: `app/models/schemas.py`
- **Config**: `app/config.py`
