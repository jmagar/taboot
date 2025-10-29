# API Examples

Examples for each endpoint. Replace placeholders.

## Create Firecrawl Job

```bash
curl -X POST http://localhost:4209/jobs/firecrawl \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: $API_KEY' \
  -d '{
    "urls": ["https://example.com/docs"],
    "mode": "crawl",
    "max_depth": 1,
    "respect_robots": true
  }'
```

**Response 202**

```json
{ "job_id": "job_01H...", "status": "queued", "queued_at": "2025-10-18T12:00:00Z" }
```

## List Jobs

```bash
curl -H 'X-API-Key: $API_KEY' 'http://localhost:4209/jobs?status=running&limit=20'
```

## Get Job Detail

```bash
curl -H 'X-API-Key: $API_KEY' http://localhost:4209/jobs/JOB_ID
```

## Stream/Tail Logs

```bash
curl -H 'X-API-Key: $API_KEY' 'http://localhost:4209/jobs/JOB_ID/logs?offset=0&limit=100'
```

## Get Result

```bash
curl -H 'X-API-Key: $API_KEY' http://localhost:4209/jobs/JOB_ID/result
```

## Sync Crawl

```bash
curl -X POST http://localhost:4209/crawl:sync \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: $API_KEY' \
  -d '{
    "urls": ["https://example.com/about"],
    "mode": "scrape",
    "render_js": false,
    "max_documents": 10
  }'
```

## Create Ingestion

```bash
curl -X POST http://localhost:4209/ingestions \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: $API_KEY' \
  -d '{
    "source": {"job_id": "job_01H..."},
    "destination": "both",
    "namespace": "lab",
    "chunking": {"strategy": "token", "chunk_size": 800, "chunk_overlap": 150},
    "embedding_model": "tei:gte-large",
    "graph_extraction": true,
    "tags": ["docs", "nginx"]
  }'
```

## Python Client Snippets

```python
import requests
API = "http://localhost:4209"
KEY = {"X-API-Key": "..."}

# Create job
r = requests.post(f"{API}/jobs/firecrawl", json={
  "urls": ["https://example.com"],
  "mode": "crawl",
  "max_depth": 1
}, headers=KEY)
job = r.json()["job_id"]

# Poll
detail = requests.get(f"{API}/jobs/{job}", headers=KEY).json()

# Logs
logs = requests.get(f"{API}/jobs/{job}/logs", params={"offset":0,"limit":100}, headers=KEY).json()

# Result
res = requests.get(f"{API}/jobs/{job}/result", headers=KEY).json()

# Ingest
ing = requests.post(f"{API}/ingestions", json={
  "source": {"job_id": job},
  "destination": "both",
  "namespace": "lab"
}, headers=KEY).json()
```
