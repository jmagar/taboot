# LlamaCrawl FastAPI Service

The FastAPI surface lets you orchestrate Firecrawl ingestion without using the CLI.

## Running the server

```bash
uv run llamacrawl-api
```

The server listens on `0.0.0.0:8000` by default. Ensure Redis, Qdrant, Neo4j, and TEI services configured in `config.yaml` are reachable before starting the API.

## Endpoints

- `POST /firecrawl/crawls` – queue a new Firecrawl job. Example payload:

  ```json
  {
    "url": "https://example.com",
    "mode": "crawl",
    "limit": 100,
    "max_depth": 2
  }
  ```

  The response contains the job identifier.

- `GET /firecrawl/crawls/{job_id}` – fetch job status, progress, and ingestion summary.
- `GET /health` – basic readiness probe.

Jobs are executed asynchronously: the `POST` endpoint returns immediately while background tasks stream crawl progress over WebSockets and trigger the ingestion pipeline once the crawl completes.
