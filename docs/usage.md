# Usage Guide

This guide covers the LlamaCrawl CLI commands, common workflows, and troubleshooting.

## CLI Overview

LlamaCrawl provides a Typer-based command-line interface with four main commands:

```bash
uv run llamacrawl [COMMAND] [OPTIONS]
```

### Available Commands

- `init` - Initialize storage backends (Qdrant, Neo4j, Redis)
- `ingest` - Ingest data from a specific source
- `query` - Query the RAG system
- `status` - Check system status and document counts

### Global Options

```bash
--config PATH         Path to config.yaml (default: ./config.yaml)
--log-level LEVEL     Override LOG_LEVEL env var (DEBUG|INFO|WARNING|ERROR|CRITICAL)
--help               Show help message
```

## Command Reference

### `init` - Initialize Infrastructure

Initialize storage backends by creating collections, indexes, and schemas.

```bash
uv run llamacrawl init [OPTIONS]
```

**Options:**
- `--force` - Recreate collections even if they exist (destructive!)

**Examples:**

```bash
# Initialize all storage backends
uv run llamacrawl init

# Force recreation (WARNING: deletes all data)
uv run llamacrawl init --force
```

**Output:**
```
✓ Qdrant: Created collection 'llamacrawl_documents'
  - Vector dimension: 1024
  - Distance metric: Cosine
  - Indexed fields: doc_id, source_type, timestamp, content_hash
✓ Neo4j: Initialized schema
  - Constraints: Document.doc_id, User.username, Email.message_id
  - Indexes: Document.source_type, Document.timestamp
✓ Redis: Connection verified
  - Memory: 64MB
  - Connected clients: 2
```

**When to Use:**
- First time setup
- After infrastructure deployment
- When forcing a complete reset (with `--force`)

### `ingest` - Ingest Data from Source

Trigger ingestion from a specific data source.

```bash
uv run llamacrawl ingest SOURCE [OPTIONS]
```

**Arguments:**
- `SOURCE` - Source name: `firecrawl`, `github`, `reddit`, `gmail`, `elasticsearch`

**Options:**
- `--full` - Force full re-ingestion (ignore cursor)
- `--limit N` - Limit number of documents to ingest

**Examples:**

```bash
# Ingest from Firecrawl (incremental if supported)
uv run llamacrawl ingest firecrawl

# Force full re-ingestion
uv run llamacrawl ingest github --full

# Limit to 100 documents
uv run llamacrawl ingest reddit --limit 100

# Ingest from all enabled sources
for source in firecrawl github reddit gmail elasticsearch; do
  uv run llamacrawl ingest $source
done
```

**Output:**
```
Starting ingestion: source=github
Loading documents...
Loaded 245 documents

Processing batch 1/3 (100 documents)
  Deduplication: 23 skipped (unchanged)
  Chunking: 77 documents → 312 chunks
  Embedding: 312 chunks (batch size: 32)
  Vector storage: 312 vectors stored
  Entity extraction: 45 entities, 78 relationships
  Graph storage: committed to Neo4j

Processing batch 2/3 (100 documents)
  ...

Ingestion complete: source=github
  Total documents: 245
  Processed: 189 (77.1%)
  Skipped (deduplication): 56 (22.9%)
  Failed: 0
  Duration: 3m 42s
```

**Errors:**

If ingestion fails, errors are logged and failed documents are added to Dead Letter Queue (DLQ):

```
ERROR: Failed to process document: doc_id=github_issue_12345
  Error: Network timeout
  Action: Added to DLQ for manual review

Ingestion complete with errors: source=github
  Processed: 232
  Failed: 13
  DLQ size: 13
```

Check DLQ with `status` command.

### `query` - Query the RAG System

Query the RAG system with natural language questions.

```bash
uv run llamacrawl query TEXT [OPTIONS]
```

**Arguments:**
- `TEXT` - Query text (use quotes for multi-word queries)

**Options:**
- `--sources LIST` - Filter by source types (comma-separated)
- `--after DATE` - Filter documents after date (YYYY-MM-DD)
- `--before DATE` - Filter documents before date (YYYY-MM-DD)
- `--top-k N` - Override top_k from config
- `--output-format FORMAT` - Output format: `text` (default) or `json`

**Examples:**

```bash
# Basic query
uv run llamacrawl query "What are the latest authentication changes?"

# Query with source filter
uv run llamacrawl query "bug reports" --sources github,reddit

# Query with date filter
uv run llamacrawl query "API updates" --after 2024-01-01

# Query with multiple filters
uv run llamacrawl query "security issues" \
  --sources github,gmail \
  --after 2024-06-01 \
  --top-k 30

# JSON output (for programmatic use)
uv run llamacrawl query "documentation updates" --output-format json
```

**Text Output:**
```
Query: What are the latest authentication changes?
Retrieved: 20 candidates
Reranked: 5 documents
Query time: 1.2s

Answer:
The latest authentication changes include migrating from session-based auth to JWT tokens [1],
implementing refresh token rotation [2], and adding support for OAuth 2.0 with Google and GitHub [3].
The migration guide recommends updating client code to handle token expiration [1].

Sources:
[1] GitHub Issue #1234: "Migrate to JWT authentication"
    https://github.com/owner/repo/issues/1234
    Score: 0.94 | Updated: 2024-09-15
    Snippet: "We're moving away from session-based auth to JWT tokens for better scalability..."

[2] GitHub PR #1250: "Add refresh token rotation"
    https://github.com/owner/repo/pull/1250
    Score: 0.89 | Updated: 2024-09-20
    Snippet: "This PR implements automatic refresh token rotation to improve security..."

[3] Documentation: "OAuth 2.0 Integration Guide"
    https://docs.example.com/oauth
    Score: 0.85 | Updated: 2024-09-25
    Snippet: "OAuth 2.0 support has been added for Google and GitHub providers..."
```

**JSON Output:**
```json
{
  "answer": "The latest authentication changes include migrating from session-based auth to JWT tokens [1]...",
  "sources": [
    {
      "id": "github_issue_1234",
      "source_type": "github",
      "title": "Migrate to JWT authentication",
      "url": "https://github.com/owner/repo/issues/1234",
      "score": 0.94,
      "snippet": "We're moving away from session-based auth...",
      "timestamp": "2024-09-15T10:30:00Z"
    }
  ],
  "query_time_ms": 1243,
  "retrieved_docs": 20,
  "reranked_docs": 5
}
```

**No Results:**
```
Query: obscure topic with no matches
Retrieved: 0 candidates

No relevant documents found. Try:
  - Broader search terms
  - Different source filters
  - Checking if data has been ingested
```

### `status` - Check System Status

Display system health and document statistics.

```bash
uv run llamacrawl status [OPTIONS]
```

**Options:**
- `--source NAME` - Show status for specific source
- `--format FORMAT` - Output format: `text` (default) or `json`

**Examples:**

```bash
# Overall status
uv run llamacrawl status

# Status for specific source
uv run llamacrawl status --source github

# JSON output
uv run llamacrawl status --format json
```

**Output:**
```
LlamaCrawl Status Report
========================

Service Health:
  ✓ Qdrant         http://localhost:7000
  ✓ Neo4j          bolt://localhost:7687
  ✓ Redis          redis://localhost:6379
  ✓ TEI Embeddings http://localhost:8080
  ✓ TEI Reranker   http://localhost:8081
  ✓ Ollama         http://localhost:11434

Document Counts:
  Total: 12,453 documents

  By Source:
    github:        5,234 (42.0%)
    firecrawl:     3,456 (27.8%)
    reddit:        2,109 (16.9%)
    gmail:         1,234 (9.9%)
    elasticsearch:   420 (3.4%)

Graph Statistics:
  Nodes: 8,932
    Document:    12,453
    User:         1,234
    Repository:      45
    Entity:        3,200

  Relationships: 24,567
    AUTHORED:      5,678
    MENTIONS:      8,901
    REPLIED_TO:    3,456
    RELATED_TO:    6,532

Last Sync:
  github:        2024-09-30 14:23:45 (2 hours ago)
  firecrawl:     2024-09-28 10:15:32 (2 days ago)
  reddit:        2024-09-30 12:00:00 (4 hours ago)
  gmail:         2024-09-30 15:30:12 (1 hour ago)
  elasticsearch: 2024-09-25 08:00:00 (5 days ago)

Dead Letter Queue:
  github:        3 failed documents
  reddit:        1 failed document
  Total:         4 failed documents
```

**Service Health Issues:**

If services are unhealthy:
```
Service Health:
  ✗ Qdrant         http://localhost:7000 (Connection refused)
  ✓ Neo4j          bolt://localhost:7687
  ✓ Redis          redis://localhost:6379
  ✓ TEI Embeddings http://localhost:8080
  ✗ TEI Reranker   http://localhost:8081 (Timeout after 5s)
  ✓ Ollama         http://localhost:11434

⚠️  Some services are unhealthy. Check docker compose logs.
```

## Common Workflows

### Initial Data Ingestion

Complete workflow for first-time setup:

```bash
# 1. Initialize infrastructure
uv run llamacrawl init

# 2. Verify services are healthy
uv run llamacrawl status

# 3. Start with simplest source (Firecrawl)
uv run llamacrawl ingest firecrawl

# 4. Verify ingestion worked
uv run llamacrawl status --source firecrawl

# 5. Test query
uv run llamacrawl query "test query from documentation"

# 6. Proceed with other sources
uv run llamacrawl ingest github
uv run llamacrawl ingest reddit
uv run llamacrawl ingest gmail
uv run llamacrawl ingest elasticsearch
```

### Incremental Updates

For sources with incremental sync:

```bash
# Run periodically (cron job or manual)
uv run llamacrawl ingest github
uv run llamacrawl ingest reddit
uv run llamacrawl ingest gmail

# Only new/modified documents are processed
```

### Full Re-ingestion

Force complete re-ingestion (useful after config changes):

```bash
# Re-ingest all data from source
uv run llamacrawl ingest github --full

# Or reinitialize completely (WARNING: deletes all data)
uv run llamacrawl init --force
uv run llamacrawl ingest github
```

### Monitoring and Maintenance

```bash
# Check status daily
uv run llamacrawl status

# Review DLQ for failed documents
uv run llamacrawl status --source github

# Re-process DLQ items (future feature)
# uv run llamacrawl reprocess-dlq github
```

### Querying Across Sources

```bash
# Search across all sources
uv run llamacrawl query "authentication security best practices"

# Filter by relevant sources
uv run llamacrawl query "API rate limiting" --sources github,firecrawl

# Time-based queries
uv run llamacrawl query "recent bug reports" --after 2024-09-01

# Combine filters
uv run llamacrawl query "database migration issues" \
  --sources github,elasticsearch \
  --after 2024-06-01 \
  --before 2024-09-30
```

## Troubleshooting

### Authentication Errors

**Symptom:** `401 Unauthorized` or `403 Forbidden` errors during ingestion

**Solutions:**
1. Verify credentials in `.env` are correct
2. Check token hasn't expired (especially OAuth tokens)
3. Verify token has required scopes/permissions:
   - GitHub: `repo`, `read:discussion`
   - Gmail: `https://www.googleapis.com/auth/gmail.readonly`
4. Test credentials directly:
   ```bash
   # GitHub
   curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

   # Reddit
   curl -u "$REDDIT_CLIENT_ID:$REDDIT_CLIENT_SECRET" \
     -A "$REDDIT_USER_AGENT" \
     https://www.reddit.com/api/v1/me
   ```

### Rate Limiting

**Symptom:** `429 Too Many Requests` errors

**Solutions:**
1. Reduce `batch_size` in config.yaml
2. Add rate limit configuration (see [Configuration Guide](configuration.md))
3. Wait before retrying (retry logic handles this automatically)
4. For GitHub: Check rate limit status:
   ```bash
   curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/rate_limit
   ```

### Out of Memory Errors

**Symptom:** Docker containers crashing, "Out of memory" errors

**Solutions:**
1. Reduce `chunk_size` in config.yaml (e.g., 512 → 256)
2. Reduce `batch_size` (e.g., 100 → 50)
3. Reduce `concurrent_sources` (e.g., 3 → 1)
4. Disable `auto_extract_entities` temporarily
5. Stop unused services (e.g., Ollama if only ingesting)
6. Monitor resources: `docker stats`

### GPU Memory Errors

**Symptom:** TEI or Ollama services failing with CUDA out-of-memory errors

**Solutions:**
1. Use smaller Ollama model: `llama3.1:3b` instead of `8b`
2. Reduce batch size for embeddings
3. Stop Ollama during ingestion (only needed for queries)
4. Monitor GPU usage: `nvidia-smi -l 1`

### Network Timeouts

**Symptom:** `Connection timeout` or `Read timeout` errors

**Solutions:**
1. Check network connectivity to services
2. Increase timeout values in retry configuration
3. Verify firewall rules allow connections
4. For remote services: check VPN/SSH tunnel is active
5. Test connectivity:
   ```bash
   curl -v http://localhost:7000/health  # Qdrant
   curl -v http://localhost:8080/health  # TEI
   ```

### Ingestion Stuck or Slow

**Symptom:** Ingestion appears frozen or very slow

**Solutions:**
1. Check logs for errors: `docker compose logs -f`
2. Verify services are healthy: `uv run llamacrawl status`
3. Check CPU/GPU usage: `htop` or `nvidia-smi`
4. Enable DEBUG logging:
   ```bash
   uv run llamacrawl ingest github --log-level DEBUG
   ```
5. Reduce batch size or concurrent sources
6. Check if source API is rate-limiting

### Empty Query Results

**Symptom:** Queries return no results even after ingestion

**Solutions:**
1. Verify documents were ingested: `uv run llamacrawl status`
2. Check if documents match query filters (date range, sources)
3. Try broader search terms
4. Verify embeddings were generated (check Qdrant):
   ```bash
   curl http://localhost:7000/collections/llamacrawl_documents
   ```
5. Check Neo4j has data:
   ```bash
   docker exec crawler-neo4j cypher-shell -u neo4j -p changeme \
     "MATCH (d:Document) RETURN count(d)"
   ```

### Dead Letter Queue (DLQ) Growing

**Symptom:** DLQ size increasing with failed documents

**Solutions:**
1. Check DLQ details: `uv run llamacrawl status`
2. Review error messages in logs
3. Common causes:
   - Malformed documents: Skip or fix source data
   - Network errors: Retry with `--full` flag
   - API errors: Check credentials and rate limits
4. Clear DLQ after fixing issues:
   ```bash
   # Future feature
   # uv run llamacrawl clear-dlq github
   ```

### Configuration Not Applied

**Symptom:** Changes to config.yaml or .env not taking effect

**Solutions:**
1. Verify file location (should be in project root)
2. Check YAML/env syntax
3. Restart services if infrastructure config changed:
   ```bash
   docker compose down && docker compose up -d
   ```
4. For Python config: no restart needed (loaded on each command)
5. Verify config is loaded:
   ```bash
   uv run llamacrawl status  # Check URLs match your config
   ```

## Advanced Usage

### Programmatic Access

Use LlamaCrawl as a library in Python code:

```python
from llamacrawl.config import load_config
from llamacrawl.ingestion.pipeline import IngestionPipeline
from llamacrawl.query.engine import QueryEngine

# Load configuration
config = load_config()

# Initialize pipeline
pipeline = IngestionPipeline(config)

# Ingest documents
documents = [...]  # Your documents
pipeline.ingest_documents("custom_source", documents)

# Query
engine = QueryEngine(config)
results = engine.query("your question", filters={"source_type": "custom_source"})
```

### Custom Scripts

Create automation scripts:

```bash
#!/bin/bash
# daily_sync.sh - Run daily incremental sync

sources=("github" "reddit" "gmail")

for source in "${sources[@]}"; do
  echo "Syncing $source..."
  uv run llamacrawl ingest "$source"

  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to sync $source"
    # Send notification (email, Slack, etc.)
  fi
done

echo "Sync complete. Status:"
uv run llamacrawl status
```

Make executable and run:
```bash
chmod +x daily_sync.sh
./daily_sync.sh
```

### Cron Job Setup

Schedule automatic syncs:

```bash
# Edit crontab
crontab -e

# Add daily sync at 2 AM
0 2 * * * cd /path/to/llamacrawl && uv run llamacrawl ingest github
30 2 * * * cd /path/to/llamacrawl && uv run llamacrawl ingest reddit
0 3 * * * cd /path/to/llamacrawl && uv run llamacrawl ingest gmail
```

## Performance Tips

1. **Batch Processing**: Increase `batch_size` for faster ingestion (if memory allows)
2. **Parallel Ingestion**: Increase `concurrent_sources` to process multiple sources simultaneously
3. **Disable Graph Extraction**: Set `auto_extract_entities: false` for faster ingestion
4. **Use Incremental Sync**: Always use incremental sync for sources that support it
5. **Tune Chunk Size**: Larger chunks (1024) reduce number of embeddings needed
6. **Reranking**: Keep reranking enabled - it significantly improves quality

## Additional Resources

- [Configuration Guide](configuration.md) - Detailed configuration reference
- [Architecture Guide](architecture.md) - System design and data flow
- [Setup Guide](setup.md) - Infrastructure setup and troubleshooting
- [LlamaIndex Documentation](https://developers.llamaindex.ai/) - Framework documentation
- [Qdrant Documentation](https://qdrant.tech/documentation/) - Vector database
- [Neo4j Documentation](https://neo4j.com/docs/) - Graph database
