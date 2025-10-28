-- PostgreSQL Schema for Taboot Relational Storage
-- THIS VERSION: 2.0.0 (2025-10-25)
-- Tables: Document, ExtractionWindow, IngestionJob, ExtractionJob, SchemaVersions
-- Execute during initialization (taboot init command)
--
-- MIGRATION STRATEGY:
-- This SQL file is the source of truth for PostgreSQL schema.
-- Manual versioning: increment version comment when making schema changes.
-- No Alembic/automated migrations - single-developer system, breaking changes OK.
-- When in doubt: wipe and rebuild (docker volume rm taboot-db).
--
-- SCHEMA ISOLATION:
-- Version 2.0.0: Introduced schema namespaces for isolation
-- - rag schema: Python RAG platform tables (documents, extractions, jobs)
-- - auth schema: TypeScript/Prisma auth tables (User, Session, Account, etc.)
-- Migration script: todos/scripts/migrate-to-schema-namespaces.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- Schema version tracking table (created first, always in public schema)
-- This table tracks all schema changes with checksums and execution metadata
CREATE TABLE IF NOT EXISTS schema_versions (
    version VARCHAR(32) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    applied_by VARCHAR(255) DEFAULT CURRENT_USER,
    description TEXT,
    checksum CHAR(64) NOT NULL,  -- SHA-256 of schema SQL
    execution_time_ms INTEGER,
    status VARCHAR(20) DEFAULT 'success' CHECK (status IN ('success', 'failed', 'rolled_back'))
);

-- Index for version lookups
CREATE INDEX IF NOT EXISTS idx_schema_versions_applied_at
ON schema_versions(applied_at DESC);


-- Create schemas for namespace isolation
CREATE SCHEMA IF NOT EXISTS rag;
CREATE SCHEMA IF NOT EXISTS auth;

-- Grant permissions to taboot user
-- Note: Replace 'taboot' with actual POSTGRES_USER if different
DO $$
BEGIN
    -- Grant schema usage and creation privileges
    EXECUTE format('GRANT ALL ON SCHEMA rag TO %I', current_user);
    EXECUTE format('GRANT ALL ON SCHEMA auth TO %I', current_user);

    -- Grant default privileges for future objects
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA rag GRANT ALL ON TABLES TO %I', current_user);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT ALL ON TABLES TO %I', current_user);
END $$;

-- Document table (ingested documents)
CREATE TABLE IF NOT EXISTS rag.documents (
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
ON rag.documents (source_type, ingested_at);

CREATE INDEX IF NOT EXISTS idx_documents_extraction_state
ON rag.documents (extraction_state);

CREATE INDEX IF NOT EXISTS idx_documents_content_hash
ON rag.documents (content_hash);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at
BEFORE UPDATE ON rag.documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Document content storage (separate from metadata for performance)
CREATE TABLE IF NOT EXISTS rag.document_content (
    doc_id UUID PRIMARY KEY REFERENCES rag.documents(doc_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_content_doc_id ON rag.document_content(doc_id);

-- ExtractionWindow table (micro-windows processed by extractors)
CREATE TABLE IF NOT EXISTS rag.extraction_windows (
    window_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id UUID NOT NULL REFERENCES rag.documents(doc_id) ON DELETE CASCADE,
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
ON rag.extraction_windows (doc_id);

CREATE INDEX IF NOT EXISTS idx_extraction_windows_doc_id_tier
ON rag.extraction_windows (doc_id, tier);

CREATE INDEX IF NOT EXISTS idx_extraction_windows_processed_at
ON rag.extraction_windows (processed_at);

-- IngestionJob table (tracks ingestion tasks)
CREATE TABLE IF NOT EXISTS rag.ingestion_jobs (
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
ON rag.ingestion_jobs (source_type, state, created_at);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_state
ON rag.ingestion_jobs (state);

-- ExtractionJob table (tracks extraction tasks per document)
CREATE TABLE IF NOT EXISTS rag.extraction_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id UUID NOT NULL REFERENCES rag.documents(doc_id) ON DELETE CASCADE,
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
ON rag.extraction_jobs (doc_id);

CREATE INDEX IF NOT EXISTS idx_extraction_jobs_state_started_at
ON rag.extraction_jobs (state, started_at);

CREATE INDEX IF NOT EXISTS idx_extraction_jobs_state
ON rag.extraction_jobs (state);

-- Comments for documentation
COMMENT ON TABLE rag.documents IS 'Ingested documents from all sources (web, GitHub, etc.)';
COMMENT ON TABLE rag.extraction_windows IS 'Micro-windows processed by Tier C LLM extraction';
COMMENT ON TABLE rag.ingestion_jobs IS 'Ingestion tasks with state tracking';
COMMENT ON TABLE rag.extraction_jobs IS 'Extraction tasks per document with tier progress';

COMMENT ON COLUMN rag.documents.content_hash IS 'SHA-256 hex digest for deduplication';
COMMENT ON COLUMN rag.documents.extraction_state IS 'Current extraction pipeline state';
COMMENT ON COLUMN rag.extraction_windows.tier IS 'Extraction tier: A (deterministic), B (spaCy), C (LLM)';
COMMENT ON COLUMN rag.extraction_windows.llm_latency_ms IS 'LLM inference time (tier C only)';
COMMENT ON COLUMN rag.extraction_windows.cache_hit IS 'Whether LLM response was cached (tier C only)';
COMMENT ON COLUMN rag.ingestion_jobs.pages_processed IS 'Number of pages/documents ingested';
COMMENT ON COLUMN rag.ingestion_jobs.chunks_created IS 'Number of semantic chunks created';
COMMENT ON COLUMN rag.extraction_jobs.retry_count IS 'Number of retry attempts (max 3)';

-- Verification queries
-- Count tables in rag schema
SELECT COUNT(*) AS table_count FROM information_schema.tables
WHERE table_schema = 'rag' AND table_name IN ('documents', 'document_content', 'extraction_windows', 'ingestion_jobs', 'extraction_jobs');
-- Expected: 5

-- Count indexes in rag schema
SELECT COUNT(*) AS index_count FROM pg_indexes
WHERE schemaname = 'rag';
-- Expected: 12+ (3 per table + primary keys)

-- Sample insert (for testing)
-- INSERT INTO rag.documents (source_url, source_type, content_hash)
-- VALUES ('https://docs.example.com', 'web', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
-- RETURNING doc_id, ingested_at, extraction_state;
