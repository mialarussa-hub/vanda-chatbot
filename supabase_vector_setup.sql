-- ============================================================================
-- SUPABASE VECTOR SEARCH SETUP
-- ============================================================================
-- This script sets up proper pgvector-based similarity search
-- Execute this in Supabase SQL Editor: https://supabase.com/dashboard/project/YOUR_PROJECT/sql
--
-- What this does:
-- 1. Enables pgvector extension
-- 2. Creates match_documents() function using native pgvector operators
-- 3. Creates HNSW index for fast vector search (O(log n) instead of O(n))
-- ============================================================================

-- Step 1: Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Verify your table name and structure
-- IMPORTANT: Replace "documents" with your actual table name if different!
-- Run this to check: SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Step 3: Create the similarity search function
-- This function uses pgvector's native <=> (cosine distance) operator
-- which is MUCH faster than calculating similarity in Python
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.75,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    -- Convert cosine distance (0-2) to similarity (0-1)
    -- <=> returns distance where 0 = identical vectors
    -- 1 - distance gives us similarity where 1 = identical
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
  -- CRITICAL: Order by the distance operator to use the index!
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Step 4: Create HNSW vector index for fast approximate nearest neighbor search
-- This index is CRITICAL for performance on large datasets
-- HNSW (Hierarchical Navigable Small World) is best for most use cases
DROP INDEX IF EXISTS documents_embedding_idx;
CREATE INDEX documents_embedding_idx
ON documents
USING hnsw (embedding vector_cosine_ops);

-- Alternative: IVFFlat index (uncomment if you prefer this)
-- IVFFlat is faster to build but slower at search time
-- Use this if you have VERY large datasets (millions of rows) and need faster indexing
-- DROP INDEX IF EXISTS documents_embedding_idx;
-- CREATE INDEX documents_embedding_idx
-- ON documents
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- Step 5: Test the function (optional but recommended)
-- This tests the function by using an existing embedding from your table
-- You should see results with similarity scores between 0.7-1.0 for good matches
DO $$
DECLARE
  test_embedding vector(1536);
BEGIN
  -- Get a random embedding from your documents table
  SELECT embedding INTO test_embedding
  FROM documents
  WHERE embedding IS NOT NULL
  LIMIT 1;

  -- Test the function
  RAISE NOTICE 'Testing match_documents function...';
  PERFORM * FROM match_documents(
    test_embedding,
    0.5,  -- Low threshold for testing
    5     -- Return 5 results
  );
  RAISE NOTICE 'Function test completed successfully!';
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE 'Test failed: %', SQLERRM;
END $$;

-- Step 6: Verify the index was created
-- Run this to confirm:
SELECT
  schemaname,
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE tablename = 'documents'
  AND indexname = 'documents_embedding_idx';

-- ============================================================================
-- EXPECTED OUTPUT:
-- ============================================================================
-- After running this script, you should see:
-- 1. "CREATE EXTENSION" confirmation
-- 2. "CREATE FUNCTION" confirmation
-- 3. "CREATE INDEX" confirmation
-- 4. Test function output (if it ran successfully)
-- 5. Index verification showing the HNSW index exists
--
-- If you see any errors:
-- - Check your table name (might not be "documents")
-- - Verify embedding column exists and is vector(1536) type
-- - Make sure you have proper permissions in Supabase
-- ============================================================================
