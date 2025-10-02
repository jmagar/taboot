# Setup Guide

This guide walks you through setting up LlamaCrawl from scratch, including infrastructure deployment, Python environment configuration, and credential setup.

## Prerequisites

### Required Software

- **Python 3.11 or higher**: Check with `python --version`
- **UV Package Manager**: Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Docker**: Install from [docker.com](https://docs.docker.com/get-docker/)
- **Docker Compose**: Included with Docker Desktop, or install separately
- **NVIDIA GPU**: Required for embeddings and LLM synthesis (RTX 4070 or better recommended)
- **NVIDIA Container Toolkit**: For GPU support in Docker ([Installation Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html))

### System Requirements

- **RAM**: 32GB+ recommended (20-40GB used by services)
- **VRAM**: 16GB+ GPU memory (for TEI embeddings, reranker, and Ollama)
- **Storage**: 100GB+ free space for vector/graph databases and model caches
- **Network**: Stable internet connection for API calls and model downloads

### Docker Context Setup (Remote Deployment)

LlamaCrawl is designed to deploy infrastructure to a remote GPU server. Set up Docker context:

```bash
# Create Docker context for remote server
docker context create docker-mcp-steamy-wsl \
  --description "Remote GPU server" \
  --docker "host=ssh://user@steamy-wsl"

# Test connection
docker --context docker-mcp-steamy-wsl ps

# Make it default (optional)
docker context use docker-mcp-steamy-wsl
```

If deploying locally, you can skip the context setup and use default Docker context.

## Infrastructure Deployment

### 1. Clone Repository

```bash
git clone <repository-url>
cd llamacrawl
```

### 2. Review Docker Compose Configuration

The `docker-compose.yaml` file defines all infrastructure services. Review the configuration:

```bash
cat docker-compose.yaml
```

Services included:
- **Qdrant**: Vector database (ports 7000, 7001)
- **Neo4j**: Graph database (ports 7474, 7687)
- **Redis**: State/cache store (port 6379)
- **TEI Embeddings**: Qwen3-Embedding-0.6B (port 8080)
- **TEI Reranker**: Qwen3-Reranker-0.6B (port 8081)
- **Ollama**: LLM for synthesis (port 11434)

### 3. Configure Environment Variables (Optional)

Create a `.env` file to override default ports:

```bash
# Port overrides (optional)
QDRANT_HTTP_PORT=7000
QDRANT_GRPC_PORT=7001
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687
REDIS_PORT=6379
TEI_HTTP_PORT=8080
TEI_RERANKER_HTTP_PORT=8081
OLLAMA_PORT=11434

# Neo4j credentials
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password_here
```

### 4. Deploy Infrastructure

```bash
# Deploy to remote server (use --context flag)
docker --context docker-mcp-steamy-wsl compose up -d

# Or deploy locally
docker compose up -d
```

### 5. Wait for Services to Start

Services may take 2-5 minutes to download models and initialize:

```bash
# Check service status
docker --context docker-mcp-steamy-wsl compose ps

# Follow logs
docker --context docker-mcp-steamy-wsl compose logs -f

# Check specific service logs
docker --context docker-mcp-steamy-wsl compose logs -f text-embeddings-inference
```

All services should show `healthy` status before proceeding.

### 6. Pull Ollama Model

Ollama requires model to be pulled explicitly:

```bash
# Pull llama3.1:8b model (recommended for synthesis)
docker --context docker-mcp-steamy-wsl exec crawler-ollama ollama pull llama3.1:8b

# Verify model is available
docker --context docker-mcp-steamy-wsl exec crawler-ollama ollama list
```

First pull may take 5-10 minutes depending on network speed.

### 7. Verify Infrastructure Health

Check that all services are responding:

```bash
# Qdrant
curl http://localhost:7000/health

# Neo4j (may take 30-60s to fully start)
curl http://localhost:7474/

# Redis
redis-cli -h localhost -p 6379 ping

# TEI Embeddings
curl http://localhost:8080/health

# TEI Reranker
curl http://localhost:8081/health

# Ollama
curl http://localhost:11434/api/tags
```

## Python Environment Setup

### 1. Install UV Package Manager

If not already installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

### 2. Create Virtual Environment and Install Dependencies

```bash
# Navigate to project directory
cd llamacrawl

# Install dependencies (UV automatically creates venv)
uv sync

# Verify installation
uv run python --version
uv run llamacrawl --version
```

### 3. Verify CLI Installation

```bash
# Test CLI is accessible
uv run llamacrawl --help

# Should display available commands:
# - init
# - ingest
# - query
# - status
```

## Credential Configuration

### 1. Copy Configuration Templates

```bash
# Copy environment template
cp .env.example .env

# Copy pipeline configuration template
cp config.example.yaml config.yaml
```

### 2. Configure Data Source Credentials

Edit `.env` file with your API keys and credentials:

```bash
$EDITOR .env
```

Required credentials by source:

#### Firecrawl (Web Scraping)
```env
FIRECRAWL_API_URL=https://firecrawl.tootie.tv
FIRECRAWL_API_KEY=fc-your-api-key-here
```

Get API key from your Firecrawl instance admin panel.

#### GitHub
```env
GITHUB_TOKEN=ghp_your-personal-access-token-here
```

Create token at [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)

Required scopes:
- `repo` (for repository access)
- `read:discussion` (for discussions)

#### Reddit
```env
REDDIT_CLIENT_ID=your-client-id-here
REDDIT_CLIENT_SECRET=your-client-secret-here
REDDIT_USER_AGENT=LlamaCrawl/1.0
```

Create app at [Reddit App Preferences](https://www.reddit.com/prefs/apps):
1. Click "create another app..."
2. Select "script" type
3. Copy client ID and secret

#### Gmail (OAuth 2.0)
```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REFRESH_TOKEN=your-refresh-token
```

OAuth setup is more complex. See [Gmail OAuth Setup](#gmail-oauth-setup) section below.

#### Elasticsearch
```env
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_API_KEY=your-elasticsearch-api-key
```

Generate API key in Kibana or using Elasticsearch API.

### 3. Configure Infrastructure URLs

Add infrastructure connection details to `.env`:

```env
# Infrastructure (adjust if using non-default ports)
QDRANT_URL=http://localhost:7000
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password_here
REDIS_URL=redis://localhost:6379
TEI_EMBEDDING_URL=http://localhost:8080
TEI_RERANKER_URL=http://localhost:8081
OLLAMA_URL=http://localhost:11434

# Logging
LOG_LEVEL=INFO
```

### 4. Configure Pipeline Settings

Edit `config.yaml` to enable data sources and configure pipeline behavior:

```bash
$EDITOR config.yaml
```

See [Configuration Guide](configuration.md) for detailed options.

## Gmail OAuth Setup

Gmail requires OAuth 2.0 authentication. Follow these steps to obtain a refresh token:

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing one
3. Enable Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

### 2. Create OAuth 2.0 Credentials

1. Navigate to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure OAuth consent screen (if prompted):
   - User Type: External (for personal use)
   - Add your email as test user
   - Scopes: `https://www.googleapis.com/auth/gmail.readonly`
4. Application type: "Desktop app"
5. Copy Client ID and Client Secret

### 3. Obtain Refresh Token

Run the OAuth flow helper:

```python
# Create auth_helper.py
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
            "client_secret": "YOUR_CLIENT_SECRET",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    },
    SCOPES
)

creds = flow.run_local_server(port=0)
print(f"Refresh Token: {creds.refresh_token}")
```

Run the helper:
```bash
python auth_helper.py
```

This will:
1. Open browser for Google authentication
2. Prompt for account selection and permissions
3. Display refresh token in terminal

### 4. Add to .env

Copy the refresh token to your `.env` file:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REFRESH_TOKEN=1//your-long-refresh-token
```

## Initialize LlamaCrawl

With infrastructure running and credentials configured, initialize storage backends:

```bash
# Create Qdrant collection, Neo4j schema, verify Redis
uv run llamacrawl init

# Expected output:
# ✓ Qdrant: Created collection 'llamacrawl_documents'
# ✓ Neo4j: Initialized schema (constraints + indexes)
# ✓ Redis: Connection verified
```

### Verify Initialization

```bash
# Check system status
uv run llamacrawl status

# Expected output:
# Service Health:
#   ✓ Qdrant
#   ✓ Neo4j
#   ✓ Redis
#   ✓ TEI Embeddings
#   ✓ TEI Reranker
#   ✓ Ollama
#
# Document Counts:
#   Total: 0
#   (no sources ingested yet)
```

## Troubleshooting

### GPU Not Detected

If TEI services fail to start with GPU errors:

```bash
# Verify NVIDIA drivers
nvidia-smi

# Verify Docker can access GPU
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu20.04 nvidia-smi

# Check NVIDIA Container Toolkit
sudo systemctl status nvidia-container-toolkit
```

### Out of Memory Errors

If services crash with OOM errors:

1. **Reduce concurrent services**: Stop Ollama if only ingesting data
2. **Use smaller models**: Try llama3.1:3b instead of 8b
3. **Adjust batch sizes**: Reduce `chunk_size` in config.yaml
4. **Monitor resources**: `docker stats` to see memory usage

### Neo4j Connection Issues

Neo4j may take 30-60 seconds to fully initialize. If connection fails:

```bash
# Check Neo4j logs
docker --context docker-mcp-steamy-wsl compose logs neo4j

# Wait for "Remote interface available at http://localhost:7474/"
# Try cypher-shell test
docker exec crawler-neo4j cypher-shell -u neo4j -p changeme "RETURN 1"
```

### Port Conflicts

If ports are already in use:

1. Edit `.env` to use different ports
2. Update URLs in `.env` to match new ports
3. Recreate containers: `docker compose down && docker compose up -d`

### Firecrawl API Errors

If Firecrawl ingestion fails:

1. Verify API URL is accessible: `curl https://firecrawl.tootie.tv/health`
2. Check API key is valid
3. Review Firecrawl instance logs for rate limits or errors

### Ollama Model Not Found

If synthesis fails with model not found:

```bash
# Pull the model explicitly
docker exec crawler-ollama ollama pull llama3.1:8b

# List available models
docker exec crawler-ollama ollama list
```

## Next Steps

After successful setup:

1. **Test ingestion**: `uv run llamacrawl ingest firecrawl` (start with simplest source)
2. **Review configuration**: See [Configuration Guide](configuration.md) for detailed options
3. **Explore CLI**: See [Usage Guide](usage.md) for command reference
4. **Understand architecture**: See [Architecture Guide](architecture.md) for system design

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [UV Package Manager](https://docs.astral.sh/uv/)
- [LlamaIndex Documentation](https://developers.llamaindex.ai/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Documentation](https://neo4j.com/docs/)
