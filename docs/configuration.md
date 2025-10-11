# Configuration Guide

LlamaCrawl uses two configuration files: `.env` for secrets and credentials, and `config.yaml` for pipeline settings.

## Configuration Files Overview

- **`.env`**: API keys, passwords, connection URLs (never commit to git)
- **`config.yaml`**: Pipeline behavior, source settings, chunking parameters

## Environment Variables (.env)

### Data Source Credentials

#### Firecrawl (Web Scraping)

```env
FIRECRAWL_API_URL=https://firecrawl.tootie.tv
FIRECRAWL_API_KEY=fc-your-api-key-here
```

- **FIRECRAWL_API_URL**: URL to your Firecrawl instance
- **FIRECRAWL_API_KEY**: API key from Firecrawl admin panel

#### GitHub

```env
GITHUB_TOKEN=ghp_your-personal-access-token-here
```

- **GITHUB_TOKEN**: Personal Access Token from [GitHub Settings](https://github.com/settings/tokens)
- Required scopes: `repo`, `read:discussion`

#### Reddit

```env
REDDIT_CLIENT_ID=your-client-id-here
REDDIT_CLIENT_SECRET=your-client-secret-here
REDDIT_USER_AGENT=LlamaCrawl/1.0
```

- **REDDIT_CLIENT_ID**: From [Reddit App Preferences](https://www.reddit.com/prefs/apps)
- **REDDIT_CLIENT_SECRET**: Secret from Reddit app
- **REDDIT_USER_AGENT**: Identifier for your app (format: `AppName/Version`)

#### Gmail (OAuth 2.0)

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REFRESH_TOKEN=1//your-long-refresh-token
```

- **GOOGLE_CLIENT_ID**: From [Google Cloud Console](https://console.cloud.google.com/)
- **GOOGLE_CLIENT_SECRET**: OAuth client secret
- **GOOGLE_OAUTH_REFRESH_TOKEN**: Obtained via OAuth flow (see [Setup Guide](setup.md#gmail-oauth-setup))

#### Elasticsearch

```env
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_API_KEY=your-elasticsearch-api-key
```

- **ELASTICSEARCH_URL**: Elasticsearch cluster URL
- **ELASTICSEARCH_API_KEY**: API key generated in Kibana or via API

### Infrastructure Connection URLs

```env
# Vector Database
QDRANT_URL=http://localhost:7000

# Graph Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password_here

# Cache/State Store
REDIS_URL=redis://localhost:6379

# Embeddings Service
TEI_EMBEDDING_URL=http://localhost:8080

# Reranking Service
TEI_RERANKER_URL=http://localhost:8081

# LLM Synthesis
OLLAMA_URL=http://localhost:11434
```

**Notes:**
- Use `localhost` if services are on same machine as Python application
- For remote deployment, replace `localhost` with server hostname/IP
- Ensure firewall rules allow connections to these ports

### Observability Settings

```env
# Logging
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Metrics (future)
PROMETHEUS_PORT=9090
```

- **LOG_LEVEL**: Controls verbosity of logging
  - `DEBUG`: Detailed diagnostic information
  - `INFO`: General informational messages (recommended)
  - `WARNING`: Warning messages only
  - `ERROR`: Error messages only
  - `CRITICAL`: Critical failures only

## Pipeline Configuration (config.yaml)

### Data Sources Configuration

#### Firecrawl

```yaml
sources:
  firecrawl:
    enabled: true
    default_crawl_depth: 3
    max_pages: 1000
    formats: [markdown, html]
```

- **enabled**: Enable/disable this source
- **default_crawl_depth**: How many levels deep to crawl (1-5 recommended)
- **max_pages**: Maximum pages to crawl per site (prevents runaway crawls)
- **formats**: Output formats to request from Firecrawl
  - `markdown`: Clean markdown text (recommended)
  - `html`: Raw HTML (use if markdown loses important structure)

#### GitHub

```yaml
sources:
  github:
    enabled: true
    repositories:
      - "owner/repo1"
      - "owner"  # ingest all repositories for this owner
    include_issues: true
    include_prs: true
    include_discussions: true
    file_extensions: [".md", ".py", ".ts", ".js", ".yaml", ".json"]
```

- **repositories**: Repository identifiers. Accepts `owner/repo` or bare `owner` to sync all
  repositories for that owner.
- **include_issues**: Whether to ingest issues and comments
- **include_prs**: Whether to ingest pull requests and reviews
- **include_discussions**: Whether to ingest GitHub discussions
- **file_extensions**: Filter repository files by extension (omit to include all)

**Incremental Sync:**
- GitHub uses `since` parameter for issues (filters by last updated time)
- PRs use Search API with timestamp queries (rate limit: 30 req/min)

#### Reddit

```yaml
sources:
  reddit:
    enabled: true
    subreddits:
      - "python"
      - "programming"
      - "MachineLearning"
    post_limit: 1000
    include_comments: true
    max_comment_depth: 5
```

- **subreddits**: List of subreddits to monitor (without `/r/` prefix)
- **post_limit**: Maximum posts per subreddit per sync (max 1000 due to Reddit API)
- **include_comments**: Whether to ingest comments on posts
- **max_comment_depth**: How deep to traverse nested comment threads

**Important:** Reddit API hard-limits all listings to 1000 items. For active subreddits, use time-windowing or reduce `post_limit`.

#### Elasticsearch

```yaml
sources:
  elasticsearch:
    enabled: true
    indices: ["docs-*", "logs-*"]
    field_mappings:
      title: "title"
      content: "body"
      timestamp: "@timestamp"
    batch_size: 500
    use_search_after: true
```

- **indices**: Index patterns to query (supports wildcards)
- **field_mappings**: Map Elasticsearch fields to LlamaCrawl document model
  - `title`: Field containing document title
  - `content`: Field containing main text content
  - `timestamp`: Field containing document timestamp
- **batch_size**: Documents per pagination request (200-1000 recommended)
- **use_search_after**: Use `search_after` + PIT (Elasticsearch 7.10+) instead of scroll API

**Incremental Sync:**
- Requires timestamp field in mapping
- Queries with `{"range": {"timestamp": {"gt": last_cursor}}}`
- Not all indices have timestamps - incremental sync may not be available

#### Gmail

```yaml
sources:
  gmail:
    enabled: true
    labels: ["INBOX", "SENT"]
    include_attachments_metadata: true
    max_results: 1000
```

- **labels**: Gmail labels to sync (e.g., `INBOX`, `SENT`, custom labels)
- **include_attachments_metadata**: Include attachment info (doesn't download files)
- **max_results**: Maximum emails per sync

**Incremental Sync:**
- Uses query-based filtering: `after:YYYY/MM/DD label:INBOX`
- Stores last sync date in Redis cursor
- Note: LlamaIndex GmailReader doesn't support Gmail `historyId` API

### Ingestion Pipeline Settings

```yaml
ingestion:
  chunk_size: 512
  chunk_overlap: 50
  batch_size: 100
  concurrent_sources: 3

  retry:
    max_attempts: 5
    initial_delay_seconds: 1
    max_delay_seconds: 60

  deduplication:
    enabled: true
    strategy: hash
```

- **chunk_size**: Target chunk size in tokens (256-1024 typical)
- **chunk_overlap**: Token overlap between chunks (prevents context loss at boundaries)
- **batch_size**: Documents to process in single batch (affects memory usage)
- **concurrent_sources**: How many sources can ingest simultaneously

**Retry Settings:**
- **max_attempts**: Maximum retry attempts for transient failures
- **initial_delay_seconds**: Starting delay between retries
- **max_delay_seconds**: Maximum delay (exponential backoff caps here)

**Deduplication:**
- **enabled**: Enable content-based deduplication
- **strategy**: Deduplication method (currently only `hash` supported)
  - Computes SHA-256 hash of normalized content
  - Skips re-embedding if content unchanged

### Query Pipeline Settings

```yaml
query:
  top_k: 20
  rerank_top_n: 5
  enable_graph_traversal: true
  synthesis_model: "llama3.1:8b"
  synthesis_temperature: 0.7
  max_context_tokens: 4096
```

- **top_k**: Number of candidates from vector search (before reranking)
- **rerank_top_n**: Number of documents after reranking (sent to synthesis)
- **enable_graph_traversal**: Use Neo4j to find related documents
- **synthesis_model**: Ollama model for answer generation
  - Recommended: `llama3.1:8b` (good quality/speed balance)
  - Larger: `llama3.1:70b` (better quality, slower, needs more VRAM)
  - Smaller: `llama3.1:3b` (faster, less accurate)
- **synthesis_temperature**: Controls randomness (0.0-1.0)
  - Lower (0.3-0.5): More focused, deterministic
  - Higher (0.7-0.9): More creative, varied
- **max_context_tokens**: Maximum context length for synthesis

### Graph Extraction Settings

```yaml
graph:
  auto_extract_entities: true
  max_keywords_per_document: 10
  relationship_extraction: true
  entity_types:
    - "PERSON"
    - "ORGANIZATION"
    - "LOCATION"
    - "TECHNOLOGY"
    - "CONCEPT"
```

- **auto_extract_entities**: Use LlamaIndex PropertyGraphIndex for automatic entity extraction
- **max_keywords_per_document**: Limit entities per document (prevents graph explosion)
- **relationship_extraction**: Extract relationships between entities
- **entity_types**: Types of entities to extract (optional filter)

**Notes:**
- Entity extraction uses LLM (Ollama) and adds processing time
- Disable for faster ingestion if graph features not needed

### Logging Configuration

```yaml
logging:
  format: json
  level: INFO
  include_fields:
    - timestamp
    - level
    - logger
    - message
    - source
    - doc_id
```

- **format**: Log output format
  - `json`: Structured JSON logs (recommended for production)
  - `text`: Human-readable text logs (good for development)
- **level**: Default log level (overridden by `LOG_LEVEL` env var)
- **include_fields**: Fields to include in structured logs

### Metrics Configuration (Future)

```yaml
metrics:
  enabled: true
  prometheus_port: 9090
  export_interval_seconds: 30
```

- **enabled**: Enable metrics collection (currently placeholder)
- **prometheus_port**: Port to expose metrics endpoint
- **export_interval_seconds**: How often to update metrics

**Note:** Full Prometheus integration is planned for future phases.

## Per-Source Configuration Examples

### Scraping a Specific Website (Firecrawl)

```yaml
sources:
  firecrawl:
    enabled: true
    urls:
      - "https://docs.example.com"
      - "https://blog.example.com"
    default_crawl_depth: 2
    max_pages: 500
    formats: [markdown]
```

Run ingestion:
```bash
uv run llamacrawl ingest firecrawl
```

### Monitoring Specific GitHub Projects

```yaml
sources:
  github:
    enabled: true
    repositories:
      - "facebook/react"
      - "microsoft"  # all repositories for Microsoft
    include_issues: true
    include_prs: false  # Skip PRs if not needed
    include_discussions: false
    file_extensions: [".md"]  # Only documentation
```

Run initial sync:
```bash
uv run llamacrawl ingest github
```

Subsequent syncs will be incremental (only fetch updated items).

### Indexing Reddit Communities

```yaml
sources:
  reddit:
    enabled: true
    subreddits:
      - "python"
      - "learnpython"
    post_limit: 500
    include_comments: true
    max_comment_depth: 3
```

Run ingestion:
```bash
uv run llamacrawl ingest reddit
```

### Bulk Import from Elasticsearch

```yaml
sources:
  elasticsearch:
    enabled: true
    indices: ["application-logs-*"]
    field_mappings:
      title: "log.message"
      content: "log.full_message"
      timestamp: "@timestamp"
    batch_size: 1000
    query:
      range:
        "@timestamp":
          gte: "2024-01-01"
          lt: "2024-12-31"
```

Run import:
```bash
uv run llamacrawl ingest elasticsearch --full
```

### Syncing Gmail Inbox

```yaml
sources:
  gmail:
    enabled: true
    labels: ["INBOX"]
    include_attachments_metadata: false
    max_results: 500
```

Run initial sync (may take time for large inboxes):
```bash
uv run llamacrawl ingest gmail
```

Incremental syncs will only fetch emails after last sync date.

## Configuration Validation

LlamaCrawl validates configuration on startup. Common validation errors:

### Missing Required Credentials

```
ERROR: Missing required environment variable: GITHUB_TOKEN
```

**Solution:** Add missing credential to `.env` file.

### Invalid Configuration Values

```
ERROR: Invalid chunk_size: must be between 128 and 2048
```

**Solution:** Adjust `chunk_size` in `config.yaml` to valid range.

### Source Not Enabled

```
WARNING: Source 'github' is not enabled in config.yaml
```

**Solution:** Set `sources.github.enabled: true` in `config.yaml`.

## Advanced Configuration

### Custom Chunk Size by Source

Override chunk size per source:

```yaml
sources:
  github:
    enabled: true
    chunking:
      chunk_size: 1024  # Larger chunks for code
      chunk_overlap: 100

  reddit:
    enabled: true
    chunking:
      chunk_size: 256  # Smaller chunks for short posts
      chunk_overlap: 25
```

### Rate Limiting

Configure rate limits to avoid API throttling:

```yaml
sources:
  github:
    enabled: true
    rate_limit:
      requests_per_minute: 50  # GitHub allows 5000/hour
      burst_size: 10

  reddit:
    enabled: true
    rate_limit:
      requests_per_minute: 30  # Reddit allows 60/minute
      burst_size: 5
```

### Custom Metadata Filters

Add custom filters for queries:

```yaml
query:
  default_filters:
    - field: source_type
      values: ["github", "gmail"]
    - field: timestamp
      operator: gte
      value: "2024-01-01"
```

## Configuration Best Practices

1. **Start Small**: Enable one source at a time, test, then add more
2. **Use Incremental Sync**: Enable for sources that support it (GitHub, Gmail, Reddit)
3. **Monitor Resources**: Adjust batch sizes if running into memory issues
4. **Tune Chunk Size**: Larger chunks (512-1024) for technical docs, smaller (256-512) for chat/email
5. **Enable Graph Extraction**: Provides better context but adds processing time
6. **Set Reasonable Limits**: Use `max_pages`, `post_limit` to prevent runaway ingestion
7. **Regular Backups**: Back up `.env` file (securely) and `config.yaml`

## Troubleshooting Configuration Issues

### Configuration Not Loading

If changes to `config.yaml` aren't taking effect:

1. Check YAML syntax: `yamllint config.yaml`
2. Verify file location (should be in project root)
3. Restart any running processes

### Authentication Failures

If getting 401/403 errors:

1. Verify credentials in `.env` are correct
2. Check token hasn't expired (especially OAuth tokens)
3. Verify token has required scopes/permissions
4. Test credentials directly with API (e.g., `curl` commands)

### Performance Issues

If ingestion is slow:

1. Increase `batch_size` (if memory allows)
2. Reduce `concurrent_sources` if CPU/GPU constrained
3. Disable `auto_extract_entities` temporarily
4. Reduce `chunk_size` to lower embedding load

## Configuration Reference Links

- [LlamaIndex Configuration](https://docs.llamaindex.ai/en/stable/getting_started/customization/)
- [Qdrant Collection Setup](https://qdrant.tech/documentation/concepts/collections/)
- [Neo4j Configuration](https://neo4j.com/docs/operations-manual/current/configuration/)
- [Redis Configuration](https://redis.io/docs/management/config/)
