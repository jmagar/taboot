# Taboot CLI Live Tests

Comprehensive live testing suite for all Taboot CLI commands using real services, actual data, and zero mocks.

## Overview

This test suite validates **every CLI command** by:
- ✅ Running actual commands against real services (Neo4j, Qdrant, Redis, etc.)
- ✅ Using live data ingestion (web, GitHub, Docker Compose, etc.)
- ✅ Testing error handling and edge cases
- ✅ Validating exit codes and output formats
- ✅ Generating detailed logs for debugging

**No mocks. No fake data. 100% live.**

## Prerequisites

### Services Must Be Running
```bash
docker compose up -d
docker compose ps  # Verify all services healthy
```

### Environment Configuration
Copy `.env.example` to `.env` and configure:
- `FIRECRAWL_API_URL` (default: http://taboot-crawler:3002)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `QDRANT_URL` (default: http://taboot-vectors:6333)
- `REDIS_URL` (default: redis://taboot-cache:6379)
- **Optional:** `GITHUB_TOKEN`, Reddit/Gmail/Elasticsearch credentials

### System Initialization
```bash
uv run python -m apps.cli.taboot_cli.main init
```

## Running Tests

### Full Test Suite
```bash
cd tests/live
bash run-all-tests.sh
```

### Individual Test Suites
```bash
bash suites/01-schema-tests.sh
bash suites/02-status-tests.sh
bash suites/03-web-ingest-tests.sh
# ... etc
```

## Test Organization

| Suite | Tests | Duration | Description |
|-------|-------|----------|-------------|
| 01-schema-tests.sh | 3 | 1 min | init, schema version, schema history |
| 02-status-tests.sh | 8 | 2 min | Global and component-specific health checks |
| 03-web-ingest-tests.sh | 3 | 5 min | Web crawling and ingestion |
| 04-github-ingest-tests.sh | 3 | 3 min | GitHub repo ingestion (requires token) |
| 05-docker-compose-tests.sh | 3 | 1 min | Docker Compose YAML parsing and ingestion |
| 06-external-sources-tests.sh | 5 | 10 min | Reddit, YouTube, Gmail, Elasticsearch, SWAG |
| 07-extraction-tests.sh | 3 | 10 min | Extraction pipeline (Tier A/B/C) |
| 08-listing-tests.sh | 4 | 2 min | Document listing with filters |
| 09-graph-tests.sh | 4 | 2 min | Cypher query execution |
| 10-query-tests.sh | 4 | 5 min | Knowledge graph retrieval and synthesis |

**Total: ~40 tests, 40-60 minutes duration**

## Test Output

Each test writes to `outputs/{test_name}.log`:

```
tests/live/outputs/
├── Schema_Version.log
├── Global_Status.log
├── Ingest_Web_example_com.log
├── Graph_Query_Count_Nodes.log
└── ... (one per test)
```

## Test Results

After running, view summary:
```bash
tail outputs/*.log
```

Or check combined results:
```bash
grep -h "^\[" outputs/*.log | sort | uniq -c
```

## Important Notes

### Data Persistence
- Tests ingest real data into live databases
- Data persists between test runs
- This is **intentional** - we have no data to lose
- To reset: `docker volume rm taboot-db taboot-vectors taboot-cache`

### Required Services
The test suite requires these Docker services healthy:
- `taboot-graph` (Neo4j)
- `taboot-vectors` (Qdrant)
- `taboot-cache` (Redis)
- `taboot-db` (PostgreSQL)
- `taboot-embed` (TEI embeddings)
- `taboot-ollama` (LLM)
- `taboot-crawler` (Firecrawl)
- `taboot-playwright` (Browser)

### Authentication
Some tests require credentials:
- **GitHub:** `GITHUB_TOKEN` env var
- **Reddit:** `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`
- **Gmail:** Google OAuth credentials
- **Elasticsearch:** Connection URL + credentials
- **Unifi:** Controller credentials
- **Tailscale:** API key

Tests are **skipped** if credentials not configured.

### Network Tests
Web ingestion requires internet connectivity:
```bash
ping -c 1 example.com  # Should succeed
```

If behind a proxy, configure Firecrawl appropriately.

## Debugging Failed Tests

### View logs
```bash
cat outputs/Test_Name.log
tail -50 outputs/Test_Name.log
```

### Re-run single test
```bash
bash suites/02-status-tests.sh
```

### Check service health
```bash
uv run python -m apps.cli.taboot_cli.main status --verbose
docker compose logs taboot-graph
docker compose ps
```

### Inspect databases
```bash
# Neo4j
docker compose exec taboot-graph cypher-shell "MATCH (n) RETURN count(n) as total;"

# Qdrant
curl http://localhost:6333/collections

# PostgreSQL
docker compose exec taboot-db psql -U postgres -d taboot -c "SELECT COUNT(*) FROM rag.documents;"

# Redis
docker compose exec taboot-cache redis-cli INFO stats
```

## Success Criteria

- ✅ All CLI commands execute without errors
- ✅ Exit codes correct (0 = success, 1 = failure)
- ✅ Data ingested into databases correctly
- ✅ Extraction pipeline processes documents
- ✅ Queries return results with citations
- ✅ Error handling works as expected
- ✅ Output formats correct (table, JSON)

## Test Dependencies

```
Tests must run in order:
01-schema-tests.sh          (initializes schema)
  ↓
02-status-tests.sh          (validates services)
  ↓
03-web-ingest-tests.sh      (creates documents)
  ↓
07-extraction-tests.sh      (processes documents)
  ↓
08-listing-tests.sh         (lists results)
  ↓
09-graph-tests.sh           (queries graph)
  ↓
10-query-tests.sh           (end-to-end retrieval)
```

Other suites (04, 05, 06) can run in parallel after 02.

## CI/CD Integration

To integrate into CI pipeline:

```yaml
# .github/workflows/live-tests.yml
name: Live CLI Tests
on: [push]

jobs:
  live-tests:
    runs-on: ubuntu-latest
    services:
      docker:
        image: docker:latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Start services
        run: docker compose up -d
      - name: Initialize
        run: uv run python -m apps.cli.taboot_cli.main init
      - name: Run tests
        run: cd tests/live && bash run-all-tests.sh
      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-logs
          path: tests/live/outputs/
```

## Performance Targets

Expected test execution times (on RTX 4070):
- **Web ingestion:** 5-10 pages in ~5 seconds
- **GitHub ingestion:** 5-10 documents in ~3 seconds
- **Docker Compose:** Parse + write in ~1 second
- **Extraction pending:** 5 documents in ~10 seconds
- **Graph queries:** <100ms per query
- **Retrieval:** 2-5 seconds (embeddings + reranking + synthesis)

If tests take significantly longer, check:
- GPU availability (`nvidia-smi`)
- Network connectivity (for web crawling)
- Service health (`docker compose logs <service>`)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused" | Start services: `docker compose up -d` |
| "Permission denied" | Check file permissions: `chmod +x *.sh` |
| Tests hang | Check GPU memory: `nvidia-smi` |
| Ingestion slow | Check network: `ping example.com` |
| Schema errors | Reset: `docker volume rm taboot-db` |
| Qdrant errors | Check vector dimension config |

## Contributing

To add new test:

1. Create test in appropriate suite or new suite
2. Follow naming convention: `test_<command>_<scenario>`
3. Use test helper functions (see run-all-tests.sh)
4. Include exit code validation
5. Log all output to `outputs/`
6. Document expected results

## License

Same as Taboot project (Proprietary)
