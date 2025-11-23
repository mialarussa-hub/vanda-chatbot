-- Enable the pg_trgm extension for fuzzy matching (optional but recommended)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Add Full Text Search (FTS) column to documents table
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS fts tsvector;

-- 2. Create a function to automatically update the FTS column
CREATE OR REPLACE FUNCTION documents_fts_update()
RETURNS trigger AS $$
BEGIN
  -- Combine content and relevant metadata for search
  NEW.fts := 
    setweight(to_tsvector('italian', COALESCE(NEW.content, '')), 'A') ||
    setweight(to_tsvector('italian', COALESCE(NEW.metadata->>'heading', '')), 'B') ||
    setweight(to_tsvector('italian', COALESCE(NEW.metadata->>'category', '')), 'C') ||
    setweight(to_tsvector('italian', COALESCE(NEW.metadata->>'tags', '')), 'C');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Create a trigger to execute the function on INSERT or UPDATE
DROP TRIGGER IF EXISTS documents_fts_trigger ON documents;
CREATE TRIGGER documents_fts_trigger
BEFORE INSERT OR UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION documents_fts_update();

-- 4. Create an index for fast FTS
CREATE INDEX IF NOT EXISTS documents_fts_idx 
ON documents 
USING GIN (fts);

-- 5. Backfill existing data (run this once)
UPDATE documents 
SET fts = 
    setweight(to_tsvector('italian', COALESCE(content, '')), 'A') ||
    setweight(to_tsvector('italian', COALESCE(metadata->>'heading', '')), 'B') ||
    setweight(to_tsvector('italian', COALESCE(metadata->>'category', '')), 'C') ||
    setweight(to_tsvector('italian', COALESCE(metadata->>'tags', '')), 'C');

-- 6. Create the Hybrid Search RPC function
-- This combines Vector Similarity (Cosine) and Keyword Match (BM25/TS_RANK)
-- using Reciprocal Rank Fusion (RRF) logic simplified.

CREATE OR REPLACE FUNCTION hybrid_search(
  query_text TEXT,
  query_embedding VECTOR(1536),
  match_count INT,
  full_text_weight FLOAT DEFAULT 1.0,
  semantic_weight FLOAT DEFAULT 1.0,
  match_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
  id BIGINT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT,
  fts_score FLOAT,
  combined_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  WITH vector_search AS (
    SELECT 
      d.id, 
      d.content, 
      d.metadata, 
      (1 - (d.embedding <=> query_embedding)) AS similarity
    FROM documents d
    WHERE 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count * 2
  ),
  keyword_search AS (
    SELECT 
      d.id, 
      d.content, 
      d.metadata, 
      ts_rank_cd(d.fts, websearch_to_tsquery('italian', query_text)) AS fts_score
    FROM documents d
    WHERE d.fts @@ websearch_to_tsquery('italian', query_text)
    ORDER BY fts_score DESC
    LIMIT match_count * 2
  )
  SELECT
    COALESCE(v.id, k.id) AS id,
    COALESCE(v.content, k.content) AS content,
    COALESCE(v.metadata, k.metadata) AS metadata,
    COALESCE(v.similarity, 0.0) AS similarity,
    COALESCE(k.fts_score, 0.0) AS fts_score,
    (
      COALESCE(v.similarity, 0.0) * semantic_weight +
      COALESCE(normalize_fts.normalized_score, 0.0) * full_text_weight
    ) AS combined_score
  FROM vector_search v
  FULL OUTER JOIN keyword_search k ON v.id = k.id
  CROSS JOIN (
    -- Normalize FTS score to 0-1 range roughly for combination
    SELECT MAX(fts_score) as max_score FROM keyword_search
  ) as max_fts
  LEFT JOIN LATERAL (
    SELECT CASE 
      WHEN max_fts.max_score > 0 THEN k.fts_score / max_fts.max_score 
      ELSE 0 
    END as normalized_score
  ) as normalize_fts ON true
  ORDER BY combined_score DESC
  LIMIT match_count;
END;
$$;
