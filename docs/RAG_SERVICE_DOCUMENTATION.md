# RAG Service - Documentazione Completa

## Panoramica

Il **RAGService** (Retrieval-Augmented Generation Service) è il componente core del chatbot VANDA che gestisce:

1. **Similarity Search**: Ricerca di documenti simili nel database vettoriale Supabase
2. **Metadata Filtering**: Filtri avanzati su categorie, client type, featured, priority, etc.
3. **Context Formatting**: Preparazione del context ottimizzato per il LLM
4. **Document Retrieval**: Recupero di documenti specifici per ID o categoria

---

## Architettura

```
┌─────────────────────────────────────────────────────────────┐
│                      User Query                              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Embedding Service                           │
│         (OpenAI text-embedding-3-small)                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼ query_embedding (1536 dims)
┌─────────────────────────────────────────────────────────────┐
│                     RAG Service                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Apply metadata filters (optional)                 │   │
│  │ 2. Fetch documents from Supabase                     │   │
│  │ 3. Calculate cosine similarity (client-side)         │   │
│  │ 4. Filter by threshold                               │   │
│  │ 5. Sort by similarity (desc)                         │   │
│  │ 6. Return top-k results                              │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼ List[DocumentChunk]
┌─────────────────────────────────────────────────────────────┐
│              Context Formatter                               │
│  (Formats documents into LLM-ready context string)          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼ formatted_context
┌─────────────────────────────────────────────────────────────┐
│                      LLM Service                             │
│         (Generates response using context)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Tabella: `public.documents`

| Column    | Type         | Description                              |
|-----------|--------------|------------------------------------------|
| `id`      | `int8`       | Primary key                              |
| `content` | `text`       | Contenuto testuale del progetto          |
| `metadata`| `jsonb`      | Metadata strutturati (vedi sotto)        |
| `embedding`| `vector(1536)`| Embedding OpenAI text-embedding-3-small |

### Struttura Metadata (JSONB)

```json
{
  "id": "unique_chunk_id",
  "url": "https://www.vandadesigners.com/...",
  "heading": "Titolo del Progetto",
  "tags": "interior design, residential, modern",
  "category": "portfolio",
  "subcategory": "interior",
  "document_type": "progetto",
  "client": "Nome Cliente",
  "client_type": "residential",
  "brand": "Brand Name",
  "visibility": "high",
  "priority": 5,
  "featured": true,
  "project_scale": "medium",
  "chunk_number": 0,
  "total_chunk": 5,
  "document_id": "base_document_id",
  "source": "blob"
}
```

---

## Modelli Pydantic

### DocumentMetadata

```python
class DocumentMetadata(BaseModel):
    id: Optional[str] = None
    url: Optional[str] = None
    heading: Optional[str] = None
    tags: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    document_type: Optional[str] = None
    client: Optional[str] = None
    client_type: Optional[str] = None
    brand: Optional[str] = None
    visibility: Optional[str] = None
    priority: Optional[int] = None
    featured: Optional[bool] = None
    project_scale: Optional[str] = None
    chunk_number: Optional[int] = None
    total_chunk: Optional[int] = None
    document_id: Optional[str] = None
    source: Optional[str] = None

    class Config:
        extra = "allow"  # Permetti campi extra
```

### DocumentChunk

```python
class DocumentChunk(BaseModel):
    id: int                          # ID database
    content: str                     # Contenuto testuale
    metadata: DocumentMetadata       # Metadata strutturati
    similarity: Optional[float]      # Cosine similarity [0, 1]
```

### MetadataFilter

```python
class MetadataFilter(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    client_type: Optional[str] = None
    visibility: Optional[str] = None
    featured: Optional[bool] = None
    min_priority: Optional[int] = None
    project_scale: Optional[str] = None
    document_type: Optional[str] = None
```

---

## API del RAGService

### `search_similar_documents()`

**Metodo principale** per similarity search con supporto filtri.

```python
def search_similar_documents(
    self,
    query_embedding: List[float],
    match_count: Optional[int] = None,        # Default: 5
    match_threshold: Optional[float] = None,   # Default: 0.75
    metadata_filter: Optional[MetadataFilter] = None
) -> List[DocumentChunk]:
```

**Parametri:**

- `query_embedding`: Vettore embedding 1536 dimensioni (da OpenAI)
- `match_count`: Numero massimo risultati da ritornare (top-k)
- `match_threshold`: Soglia minima similarity (0-1). Solo documenti >= threshold
- `metadata_filter`: Filtri opzionali per metadata JSONB

**Returns:**

- Lista di `DocumentChunk` ordinati per similarity (maggiore a minore)

**Esempio:**

```python
from app.services.rag_service import rag_service
from app.services.embedding_service import embedding_service
from app.models.schemas import MetadataFilter

# 1. Genera embedding della query
query = "Progetti di interior design residenziale"
query_embedding = embedding_service.get_embedding(query)

# 2. Definisci filtri (opzionale)
filters = MetadataFilter(
    category="portfolio",
    client_type="residential",
    featured=True,
    min_priority=5
)

# 3. Cerca documenti simili
documents = rag_service.search_similar_documents(
    query_embedding=query_embedding,
    match_count=5,
    match_threshold=0.75,
    metadata_filter=filters
)

# 4. Usa i risultati
for doc in documents:
    print(f"Similarity: {doc.similarity:.4f}")
    print(f"Heading: {doc.metadata.heading}")
    print(f"Content: {doc.content[:200]}...")
```

---

### `format_context_for_llm()`

Formatta i documenti recuperati in un context string ottimizzato per il LLM.

```python
def format_context_for_llm(
    self,
    documents: List[DocumentChunk],
    include_metadata: bool = True,
    max_context_length: Optional[int] = None
) -> str:
```

**Parametri:**

- `documents`: Lista documenti da formattare
- `include_metadata`: Se True, include heading, category, tags, etc.
- `max_context_length`: Lunghezza max in caratteri (truncate se supera)

**Returns:**

- String formattato pronto per essere inserito nel prompt LLM

**Esempio Output:**

```
INFORMAZIONI RILEVANTI DAL DATABASE VANDA DESIGNERS:
(Trovati 3 documenti rilevanti)
================================================================================

[DOCUMENTO 1]
Titolo: Interior Design di un appartamento nel Cuore di Burgos
Categoria: portfolio
Tipo Cliente: residential
Tags: interior design, ristrutturazione, arredi su misura
Rilevanza: 89.45%

Contenuto:
Il progetto riguarda la ristrutturazione completa di un appartamento...
--------------------------------------------------------------------------------

[DOCUMENTO 2]
...
```

---

### `get_document_by_id()`

Recupera un documento specifico per ID primario.

```python
def get_document_by_id(self, doc_id: int) -> Optional[DocumentChunk]:
```

**Esempio:**

```python
document = rag_service.get_document_by_id(123)

if document:
    print(f"Found: {document.metadata.heading}")
```

---

### `get_documents_by_category()`

Recupera documenti per categoria (senza similarity search).

```python
def get_documents_by_category(
    self,
    category: str,
    limit: int = 10
) -> List[DocumentChunk]:
```

**Esempio:**

```python
portfolio_docs = rag_service.get_documents_by_category(
    category="portfolio",
    limit=10
)

for doc in portfolio_docs:
    print(doc.metadata.heading)
```

---

### `get_database_stats()`

Ritorna statistiche sul database.

```python
def get_database_stats(self) -> Dict[str, Any]:
```

**Esempio:**

```python
stats = rag_service.get_database_stats()
print(f"Total documents: {stats['total_documents']}")
print(f"Status: {stats['status']}")
```

---

## Configurazione

### File: `app/config.py`

```python
# RAG Configuration
RAG_DEFAULT_MATCH_COUNT: int = 5           # Top-k risultati
RAG_DEFAULT_MATCH_THRESHOLD: float = 0.75  # Soglia similarity
RAG_MAX_CONTEXT_LENGTH: int = 8000         # Max chars context
RAG_ENABLE_METADATA_FILTERS: bool = True   # Abilita filtri
```

### Variabili d'Ambiente (.env)

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
SUPABASE_TABLE_NAME=documents

# OpenAI
OPENAI_API_KEY=sk-...
```

---

## Filtri Metadata Supportati

Il RAGService supporta i seguenti filtri JSONB:

| Filtro           | Tipo    | Operatore | Descrizione                    |
|------------------|---------|-----------|--------------------------------|
| `category`       | `str`   | `eq`      | Categoria esatta               |
| `subcategory`    | `str`   | `eq`      | Sottocategoria esatta          |
| `client_type`    | `str`   | `eq`      | Tipo cliente esatto            |
| `visibility`     | `str`   | `eq`      | Livello visibilità esatto      |
| `featured`       | `bool`  | `eq`      | Solo progetti featured         |
| `min_priority`   | `int`   | `gte`     | Priorità >= valore             |
| `project_scale`  | `str`   | `eq`      | Scala progetto esatta          |
| `document_type`  | `str`   | `eq`      | Tipo documento esatto          |

**Esempio Combinato:**

```python
filters = MetadataFilter(
    category="portfolio",          # Portfolio only
    client_type="residential",     # Residential only
    featured=True,                 # Featured only
    min_priority=7,                # Priority >= 7
    project_scale="large"          # Large projects only
)
```

---

## Cosine Similarity

Il RAGService calcola la **cosine similarity** tra embedding della query ed embedding dei documenti:

```
similarity = (A · B) / (||A|| * ||B||)
```

Dove:
- `A · B` = dot product
- `||A||` = norma euclidea di A
- `||B||` = norma euclidea di B

**Range:** [0, 1]
- **1.0** = Identici (perfetta corrispondenza)
- **0.8-0.9** = Molto simili (alta rilevanza)
- **0.7-0.8** = Abbastanza simili (rilevanza media)
- **< 0.7** = Poco simili (bassa rilevanza)

### Threshold Consigliati

| Use Case               | Threshold | Descrizione                         |
|------------------------|-----------|-------------------------------------|
| Alta precisione        | 0.80-0.85 | Solo risultati molto rilevanti      |
| Bilanciato (default)   | 0.75      | Buon balance precisione/recall      |
| Alta recall            | 0.65-0.70 | Più risultati, meno precisi         |
| Esplorazione           | 0.60      | Massima copertura                   |

---

## Performance Note

### IMPORTANTE: Similarity Calculation Client-Side

⚠️ **Attualmente il calcolo della similarity è fatto client-side** (in Python).

Questo significa che:
1. Tutti i documenti (o documenti filtrati) vengono scaricati da Supabase
2. Gli embeddings vengono caricati in memoria
3. La similarity viene calcolata in Python (numpy)
4. I risultati vengono filtrati e ordinati

**Limitazioni:**
- Performance degradano con molti documenti (>10k)
- Latenza aumenta (network + computation)
- Consumo memoria elevato

### Soluzione: PostgreSQL Stored Procedure

Per **produzione**, si consiglia di creare una stored procedure PostgreSQL che:
1. Calcola similarity direttamente nel database (pgvector extension)
2. Applica threshold e top-k nel database
3. Ritorna solo i risultati rilevanti

**Esempio SQL:**

```sql
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(1536),
  match_count int DEFAULT 5,
  match_threshold float DEFAULT 0.75,
  filter_category text DEFAULT NULL,
  filter_client_type text DEFAULT NULL
)
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.content,
    d.metadata,
    1 - (d.embedding <=> query_embedding) as similarity
  FROM documents d
  WHERE
    (filter_category IS NULL OR d.metadata->>'category' = filter_category)
    AND (filter_client_type IS NULL OR d.metadata->>'client_type' = filter_client_type)
    AND (1 - (d.embedding <=> query_embedding)) >= match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;
```

Poi usarla dal RAGService:

```python
response = self.client.rpc('match_documents', {
    'query_embedding': query_embedding,
    'match_count': match_count,
    'match_threshold': match_threshold,
    'filter_category': metadata_filter.category if metadata_filter else None,
    'filter_client_type': metadata_filter.client_type if metadata_filter else None
}).execute()
```

---

## Testing

### Run Test Suite

```bash
cd D:\PROGETTI\AGENTIKA\WEB\vanda-chatbot
python examples/test_rag_service.py
```

### Test Disponibili

1. **Basic Similarity Search**: Search senza filtri
2. **Filtered Search**: Search con filtri metadata
3. **Context Formatting**: Formattazione context per LLM
4. **Get By ID**: Fetch documento specifico
5. **Get By Category**: Browse per categoria
6. **Database Stats**: Statistiche database

---

## Troubleshooting

### Errore: "Expected 1536 dimensions, got X"

**Causa:** Embedding dimension errata.

**Soluzione:** Assicurati di usare `text-embedding-3-small`:

```python
embedding_service.model = "text-embedding-3-small"
```

---

### Errore: "No documents found"

**Causa:** Filtri troppo restrittivi o database vuoto.

**Soluzione:**
1. Verifica che il database contenga documenti: `rag_service.get_database_stats()`
2. Rimuovi i filtri metadata
3. Abbassa il threshold

---

### Similarity Troppo Bassa

**Causa:** Query non rappresentativa del contenuto.

**Soluzione:**
1. Riformula la query con keywords più specifiche
2. Abbassa il threshold a 0.65-0.70
3. Aumenta `match_count` per vedere più risultati

---

## Roadmap

### Short-term
- [x] Implementazione base RAGService
- [x] Metadata filters
- [x] Context formatting
- [ ] Caching dei risultati (Redis)
- [ ] Rate limiting per OpenAI API

### Long-term
- [ ] Stored procedure PostgreSQL per similarity search
- [ ] Reranking con modelli dedicati (Cohere, etc.)
- [ ] Hybrid search (keyword + semantic)
- [ ] Query expansion
- [ ] User feedback loop per migliorare relevance

---

## Credits

- **Framework**: FastAPI, Supabase, OpenAI
- **Vector DB**: Supabase (pgvector)
- **Embeddings**: OpenAI text-embedding-3-small
- **Validation**: Pydantic v2
- **Logging**: Loguru
