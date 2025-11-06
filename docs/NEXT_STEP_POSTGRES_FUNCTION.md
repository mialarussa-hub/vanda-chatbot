# Next Step: PostgreSQL Stored Procedure per Similarity Search

## Problema Attuale

Il RAGService **calcola la similarity client-side** (in Python), il che significa:

1. Tutti i documenti (o documenti filtrati) vengono scaricati da Supabase
2. Gli embeddings (1536 dimensioni × N documenti) vengono caricati in memoria
3. La similarity viene calcolata in Python usando numpy
4. I risultati vengono filtrati, ordinati e limitati

### Limitazioni

- **Performance**: Con 337 documenti va bene, ma con 10k+ documenti degrada
- **Latency**: Network transfer + computation time
- **Memory**: Caricamento di tutti gli embeddings in RAM
- **Scalability**: Non scala bene con database grandi

---

## Soluzione: Stored Procedure PostgreSQL

Supabase usa **PostgreSQL con pgvector extension**, che supporta:

- **Cosine similarity nativa** (operatore `<=>`)
- **Index HNSW** per similarity search veloce
- **Filtering e sorting nel database**

### Vantaggi

- **10-100x più veloce** per database grandi
- **Riduce network transfer** (solo risultati finali)
- **Riduce memoria client** (no caricamento embeddings)
- **Scalabile** con milioni di documenti

---

## Step 1: Crea Stored Procedure

### SQL Function: `match_documents`

Esegui questo SQL nel **SQL Editor di Supabase**:

```sql
-- ============================================================================
-- FUNCTION: match_documents
-- Cerca documenti simili usando cosine similarity con filtri metadata
-- ============================================================================

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(1536),
  match_count int DEFAULT 5,
  match_threshold float DEFAULT 0.75,
  filter_category text DEFAULT NULL,
  filter_subcategory text DEFAULT NULL,
  filter_client_type text DEFAULT NULL,
  filter_visibility text DEFAULT NULL,
  filter_featured boolean DEFAULT NULL,
  filter_min_priority int DEFAULT NULL,
  filter_project_scale text DEFAULT NULL,
  filter_document_type text DEFAULT NULL
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
    -- Calcola cosine similarity (1 - cosine distance)
    -- Operatore <=> ritorna cosine distance [0, 2]
    -- Convertiamo in similarity [0, 1]
    (1 - (d.embedding <=> query_embedding)) as similarity
  FROM documents d
  WHERE
    -- Applica filtri metadata (solo se specificati)
    (filter_category IS NULL OR d.metadata->>'category' = filter_category)
    AND (filter_subcategory IS NULL OR d.metadata->>'subcategory' = filter_subcategory)
    AND (filter_client_type IS NULL OR d.metadata->>'client_type' = filter_client_type)
    AND (filter_visibility IS NULL OR d.metadata->>'visibility' = filter_visibility)
    AND (filter_featured IS NULL OR (d.metadata->>'featured')::boolean = filter_featured)
    AND (filter_min_priority IS NULL OR (d.metadata->>'priority')::int >= filter_min_priority)
    AND (filter_project_scale IS NULL OR d.metadata->>'project_scale' = filter_project_scale)
    AND (filter_document_type IS NULL OR d.metadata->>'document_type' = filter_document_type)
    -- Filtra per threshold
    AND (1 - (d.embedding <=> query_embedding)) >= match_threshold
  -- Ordina per similarity (decrescente)
  ORDER BY similarity DESC
  -- Limita risultati (top-k)
  LIMIT match_count;
END;
$$;

-- Grant execute permissions (adjust role name if needed)
GRANT EXECUTE ON FUNCTION match_documents TO anon, authenticated;
```

### Test della Function

```sql
-- Test con embedding fittizio (in realtà useresti un vero embedding da OpenAI)
SELECT
  id,
  metadata->>'heading' as heading,
  similarity
FROM match_documents(
  query_embedding := (SELECT embedding FROM documents LIMIT 1),
  match_count := 5,
  match_threshold := 0.75,
  filter_category := 'portfolio',
  filter_client_type := 'residential'
);
```

---

## Step 2: Crea Index HNSW (Opzionale ma Raccomandato)

Per **performance ottimali** con database grandi, crea un index HNSW:

```sql
-- ============================================================================
-- INDEX: HNSW per fast similarity search
-- IMPORTANTE: Questo migliora drasticamente le performance con >1k documenti
-- ============================================================================

-- Crea index HNSW con cosine distance
CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx
ON documents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Parametri:
-- m = 16: Numero connessioni per layer (default)
-- ef_construction = 64: Qualità index (più alto = più accurato ma più lento)

-- Per database MOLTO grandi (>100k docs), considera:
-- CREATE INDEX documents_embedding_hnsw_idx
-- ON documents
-- USING hnsw (embedding vector_cosine_ops)
-- WITH (m = 32, ef_construction = 128);
```

### Verifica Index

```sql
-- Controlla che l'index sia stato creato
SELECT
  indexname,
  indexdef
FROM pg_indexes
WHERE tablename = 'documents'
  AND indexname = 'documents_embedding_hnsw_idx';
```

---

## Step 3: Aggiorna RAGService

Modifica `app/services/rag_service.py` per usare la stored procedure:

```python
def search_similar_documents(
    self,
    query_embedding: List[float],
    match_count: Optional[int] = None,
    match_threshold: Optional[float] = None,
    metadata_filter: Optional[MetadataFilter] = None
) -> List[DocumentChunk]:
    """
    Cerca documenti simili usando vector similarity search.

    NOTA: Usa stored procedure PostgreSQL per performance ottimali.
    """
    try:
        # Usa valori default se non specificati
        if match_count is None:
            match_count = self.default_match_count
        if match_threshold is None:
            match_threshold = self.default_match_threshold

        # Validazione embedding
        if len(query_embedding) != self.embedding_dimension:
            raise ValueError(
                f"Expected {self.embedding_dimension} dimensions, "
                f"got {len(query_embedding)}"
            )

        logger.info(
            f"Searching similar documents - "
            f"match_count: {match_count}, threshold: {match_threshold}"
        )

        # Prepara parametri per RPC call
        params = {
            'query_embedding': query_embedding,
            'match_count': match_count,
            'match_threshold': match_threshold,
            'filter_category': None,
            'filter_subcategory': None,
            'filter_client_type': None,
            'filter_visibility': None,
            'filter_featured': None,
            'filter_min_priority': None,
            'filter_project_scale': None,
            'filter_document_type': None
        }

        # Applica filtri metadata se forniti
        if metadata_filter:
            if metadata_filter.category:
                params['filter_category'] = metadata_filter.category
            if metadata_filter.subcategory:
                params['filter_subcategory'] = metadata_filter.subcategory
            if metadata_filter.client_type:
                params['filter_client_type'] = metadata_filter.client_type
            if metadata_filter.visibility:
                params['filter_visibility'] = metadata_filter.visibility
            if metadata_filter.featured is not None:
                params['filter_featured'] = metadata_filter.featured
            if metadata_filter.min_priority is not None:
                params['filter_min_priority'] = metadata_filter.min_priority
            if metadata_filter.project_scale:
                params['filter_project_scale'] = metadata_filter.project_scale
            if metadata_filter.document_type:
                params['filter_document_type'] = metadata_filter.document_type

        # Chiama stored procedure
        response = self.client.rpc('match_documents', params).execute()

        if not response.data:
            logger.warning("No documents found matching criteria")
            return []

        logger.info(f"Found {len(response.data)} relevant documents")

        # Converti in DocumentChunk Pydantic models
        chunks = []
        for r in response.data:
            try:
                chunks.append(DocumentChunk(
                    id=r['id'],
                    content=r['content'],
                    metadata=DocumentMetadata(**r['metadata']),
                    similarity=round(r['similarity'], 4)
                ))
            except Exception as e:
                logger.error(f"Error creating DocumentChunk: {e}")
                continue

        if chunks:
            logger.debug(
                f"Top similarity: {chunks[0].similarity:.4f}, "
                f"Bottom: {chunks[-1].similarity:.4f}"
            )

        return chunks

    except Exception as e:
        logger.error(f"Error in similarity search: {e}")
        return []
```

---

## Step 4: Benchmark Performance

Crea un test di performance per confrontare client-side vs server-side:

```python
import time
from app.services.rag_service import rag_service
from app.services.embedding_service import embedding_service

def benchmark_similarity_search():
    """Confronta performance client-side vs server-side"""

    query = "Progetti di interior design moderno"
    query_embedding = embedding_service.get_embedding(query)

    # Test 1: Client-side (metodo attuale)
    start = time.time()
    docs_client = rag_service.search_similar_documents_client_side(
        query_embedding=query_embedding,
        match_count=10,
        match_threshold=0.75
    )
    time_client = time.time() - start

    # Test 2: Server-side (stored procedure)
    start = time.time()
    docs_server = rag_service.search_similar_documents(
        query_embedding=query_embedding,
        match_count=10,
        match_threshold=0.75
    )
    time_server = time.time() - start

    print("BENCHMARK RESULTS:")
    print(f"Client-side: {time_client:.3f}s")
    print(f"Server-side: {time_server:.3f}s")
    print(f"Speedup: {time_client / time_server:.2f}x")
```

---

## Performance Attesi

### Database Piccoli (< 1k docs)

| Metodo       | Latency | Note                              |
|--------------|---------|-----------------------------------|
| Client-side  | ~500ms  | OK per prototyping                |
| Server-side  | ~50ms   | 10x più veloce                    |

### Database Medi (1k - 10k docs)

| Metodo       | Latency | Note                              |
|--------------|---------|-----------------------------------|
| Client-side  | ~3-5s   | Inizia a degradare                |
| Server-side  | ~100ms  | 30-50x più veloce                 |

### Database Grandi (10k - 100k docs)

| Metodo       | Latency | Note                              |
|--------------|---------|-----------------------------------|
| Client-side  | >30s    | Impraticabile                     |
| Server-side  | ~200ms  | Con HNSW index, >100x più veloce  |

---

## Monitoring Query Performance

### Abilita Query Stats in PostgreSQL

```sql
-- Abilita query timing
SET track_io_timing = on;

-- Analizza performance di una query
EXPLAIN ANALYZE
SELECT
  id,
  metadata->>'heading' as heading,
  (1 - (embedding <=> '[0.1, 0.2, ...]'::vector)) as similarity
FROM documents
WHERE (1 - (embedding <=> '[0.1, 0.2, ...]'::vector)) >= 0.75
ORDER BY similarity DESC
LIMIT 5;
```

---

## Advanced: Hybrid Search

Per risultati ancora migliori, combina **semantic search** (embeddings) con **keyword search** (full-text):

```sql
CREATE OR REPLACE FUNCTION hybrid_search(
  query_embedding vector(1536),
  query_text text,
  match_count int DEFAULT 5,
  semantic_weight float DEFAULT 0.7,
  keyword_weight float DEFAULT 0.3
)
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  semantic_score float,
  keyword_score float,
  hybrid_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.content,
    d.metadata,
    -- Semantic similarity
    (1 - (d.embedding <=> query_embedding)) as semantic_score,
    -- Keyword similarity (BM25)
    ts_rank_cd(to_tsvector('italian', d.content), plainto_tsquery('italian', query_text)) as keyword_score,
    -- Hybrid score (weighted average)
    (
      semantic_weight * (1 - (d.embedding <=> query_embedding)) +
      keyword_weight * ts_rank_cd(to_tsvector('italian', d.content), plainto_tsquery('italian', query_text))
    ) as hybrid_score
  FROM documents d
  ORDER BY hybrid_score DESC
  LIMIT match_count;
END;
$$;
```

---

## Checklist Implementazione

- [ ] Crea stored procedure `match_documents` in Supabase
- [ ] Testa la function con query di esempio
- [ ] Crea index HNSW per performance
- [ ] Aggiorna `RAGService.search_similar_documents()` per usare RPC
- [ ] (Opzionale) Mantieni metodo client-side come fallback
- [ ] Benchmark performance (client vs server)
- [ ] Deploy in production
- [ ] Monitor performance con Supabase dashboard

---

## Risorse

- **pgvector docs**: https://github.com/pgvector/pgvector
- **Supabase vector guide**: https://supabase.com/docs/guides/ai/vector-indexes
- **HNSW algorithm**: https://arxiv.org/abs/1603.09320

---

## Supporto

Per domande o problemi:
1. Controlla i logs di PostgreSQL in Supabase Dashboard
2. Verifica che l'extension pgvector sia abilitata: `SELECT * FROM pg_extension WHERE extname = 'vector';`
3. Testa la function manualmente nell'SQL Editor
