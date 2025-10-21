-- PostgreSQL Schema for Taboot Relational Storage
-- Tables: Document, ExtractionWindow, IngestionJob, ExtractionJob
-- Execute during initialization (taboot init command)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Document table (ingested documents)
CREATE TABLE IF NOT EXISTS documents (
    doc_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_url VARCHAR(2048) NOT NULL,
    source_type VARCHAR(32) NOT NULL CHECK (source_type IN (
        'web', 'github', 'reddit', 'youtube', 'gmail', 'elasticsearch',
        'docker_compose', 'swag', 'tailscale', 'unifi', 'ai_session'
    )),
    content_hash CHAR(64) NOT NULL UNIQUE,  -- SHA-256 hex digest
    ingested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    extraction_state VARCHAR(32) NOT NULL DEFAULT 'pending' CHECK (extraction_state IN (
        'pending', 'tier_a_done', 'tier_b_done', 'tier_c_done', 'completed', 'failed'
    )),
    extraction_version VARCHAR(32),  -- Semver tag (e.g., 'v1.0.0')
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB
);

-- Indexes on documents table
CREATE INDEX IF NOT EXISTS idx_documents_source_type_ingested_at
ON documents (source_type, ingested_at);

CREATE INDEX IF NOT EXISTS idx_documents_extraction_state
ON documents (extraction_state);

CREATE INDEX IF NOT EXISTS idx_documents_content_hash
ON documents (content_hash);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ExtractionWindow table (micro-windows processed by extractors)
CREATE TABLE IF NOT EXISTS extraction_windows (
    window_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    content TEXT NOT NULL CHECK (LENGTH(content) >= 1 AND LENGTH(content) <= 2048),
    tier CHAR(1) NOT NULL CHECK (tier IN ('A', 'B', 'C')),
    triples_generated INT NOT NULL DEFAULT 0 CHECK (triples_generated >= 0),
    llm_latency_ms INT CHECK (llm_latency_ms >= 0),  -- Only for tier C
    cache_hit BOOLEAN,  -- Only for tier C
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    extraction_version VARCHAR(32)
);

-- Indexes on extraction_windows table
CREATE INDEX IF NOT EXISTS idx_extraction_windows_doc_id
ON extraction_windows (doc_id);

CREATE INDEX IF NOT EXISTS idx_extraction_windows_doc_id_tier
ON extraction_windows (doc_id, tier);

CREATE INDEX IF NOT EXISTS idx_extraction_windows_processed_at
ON extraction_windows (processed_at);

-- IngestionJob table (tracks ingestion tasks)
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(32) NOT NULL CHECK (source_type IN (
        'web', 'github', 'reddit', 'youtube', 'gmail', 'elasticsearch',
        'docker_compose', 'swag', 'tailscale', 'unifi', 'ai_session'
    )),
    source_target VARCHAR(2048) NOT NULL,  -- URL, repo name, file path
    state VARCHAR(32) NOT NULL DEFAULT 'pending' CHECK (state IN (
        'pending', 'running', 'completed', 'failed'
    )),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    pages_processed INT NOT NULL DEFAULT 0 CHECK (pages_processed >= 0),
    chunks_created INT NOT NULL DEFAULT 0 CHECK (chunks_created >= 0),
    errors JSONB,
    CONSTRAINT ingestion_jobs_started_at_check CHECK (
        started_at IS NULL OR started_at >= created_at
    ),
    CONSTRAINT ingestion_jobs_completed_at_check CHECK (
        completed_at IS NULL OR completed_at >= started_at
    )
);

-- Indexes on ingestion_jobs table
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_source_type_state_created_at
ON ingestion_jobs (source_type, state, created_at);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_state
ON ingestion_jobs (state);

-- ExtractionJob table (tracks extraction tasks per document)
CREATE TABLE IF NOT EXISTS extraction_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    state VARCHAR(32) NOT NULL DEFAULT 'pending' CHECK (state IN (
        'pending', 'tier_a_done', 'tier_b_done', 'tier_c_done', 'completed', 'failed'
    )),
    tier_a_triples INT NOT NULL DEFAULT 0 CHECK (tier_a_triples >= 0),
    tier_b_windows INT NOT NULL DEFAULT 0 CHECK (tier_b_windows >= 0),
    tier_c_triples INT NOT NULL DEFAULT 0 CHECK (tier_c_triples >= 0),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    retry_count INT NOT NULL DEFAULT 0 CHECK (retry_count >= 0 AND retry_count <= 3),
    errors JSONB,
    CONSTRAINT extraction_jobs_started_at_check CHECK (
        started_at IS NULL OR started_at <= NOW()
    ),
    CONSTRAINT extraction_jobs_completed_at_check CHECK (
        completed_at IS NULL OR completed_at >= started_at
    )
);

-- Indexes on extraction_jobs table
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_doc_id
ON extraction_jobs (doc_id);

CREATE INDEX IF NOT EXISTS idx_extraction_jobs_state_started_at
ON extraction_jobs (state, started_at);

CREATE INDEX IF NOT EXISTS idx_extraction_jobs_state
ON extraction_jobs (state);

-- Comments for documentation
COMMENT ON TABLE documents IS 'Ingested documents from all sources (web, GitHub, etc.)';
COMMENT ON TABLE extraction_windows IS 'Micro-windows processed by Tier C LLM extraction';
COMMENT ON TABLE ingestion_jobs IS 'Ingestion tasks with state tracking';
COMMENT ON TABLE extraction_jobs IS 'Extraction tasks per document with tier progress';

COMMENT ON COLUMN documents.content_hash IS 'SHA-256 hex digest for deduplication';
COMMENT ON COLUMN documents.extraction_state IS 'Current extraction pipeline state';
COMMENT ON COLUMN extraction_windows.tier IS 'Extraction tier: A (deterministic), B (spaCy), C (LLM)';
COMMENT ON COLUMN extraction_windows.llm_latency_ms IS 'LLM inference time (tier C only)';
COMMENT ON COLUMN extraction_windows.cache_hit IS 'Whether LLM response was cached (tier C only)';
COMMENT ON COLUMN ingestion_jobs.pages_processed IS 'Number of pages/documents ingested';
COMMENT ON COLUMN ingestion_jobs.chunks_created IS 'Number of semantic chunks created';
COMMENT ON COLUMN extraction_jobs.retry_count IS 'Number of retry attempts (max 3)';

-- Verification queries
-- Count tables
SELECT COUNT(*) AS table_count FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ('documents', 'extraction_windows', 'ingestion_jobs', 'extraction_jobs');
-- Expected: 4

-- Count indexes
SELECT COUNT(*) AS index_count FROM pg_indexes
WHERE schemaname = 'public';
-- Expected: 12+ (3 per table + primary keys)

-- Sample insert (for testing)
-- INSERT INTO documents (source_url, source_type, content_hash)
-- VALUES ('https://docs.example.com', 'web', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
-- RETURNING doc_id, ingested_at, extraction_state;
