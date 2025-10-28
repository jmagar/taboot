# syntax=docker/dockerfile:1.7-labs

# -------------------------------
# Builder stage
# -------------------------------
FROM python:3.13-slim AS builder

# Enable fail-fast: exit immediately on error, fail on pipe errors, fail on undefined variables
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ARG DEBIAN_FRONTEND=noninteractive

# System dependencies for building Python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      git \
      curl \
      ca-certificates \
      libpq-dev \
      pkg-config \
      python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, reproducible installs
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Copy API package definition (minimal: fastapi, uvicorn, pydantic)
# Note: README.md exists in apps/api context
COPY pyproject.toml README.md ./

# Install API dependencies + runtime deps for packages/* (NO torch/spacy/transformers)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv && \
    uv pip install \
      "fastapi>=0.119.0,<1" \
      "uvicorn>=0.37.0,<1" \
      "pydantic>=2.12.0,<3" \
      "pydantic-settings>=2.7.0,<3" \
      "python-dotenv>=1.1.1,<2" \
      "python-json-logger>=4.0.0,<5" \
      "redis>=5.0.1,<6" \
      "neo4j>=5.26.0,<6" \
      "qdrant-client>=1.15.1,<2" \
      "psycopg2-binary>=2.9.11,<3" \
      "httpx>=0.28.1,<1" \
      "pyyaml>=6.0.3,<7" \
      "slowapi>=0.1.9,<1" \
      "prometheus-client>=0.21.0,<1" \
      "llama-index-core>=0.14.4,<1" \
      "llama-index-readers-web>=0.5.5,<1" \
      "llama-index-readers-github>=0.8.2,<1" \
      "llama-index-readers-file>=0.5.4,<1" \
      "llama-index-readers-youtube-transcript>=0.4.1,<1" \
      "llama-index-vector-stores-qdrant>=0.8.6,<1" \
      "llama-index-graph-stores-neo4j>=0.5.1,<1" \
      "llama-index-llms-ollama>=0.3.0,<1" \
      "llama-index-embeddings-huggingface>=0.3.0,<1" \
      "firecrawl-py>=4.4.0,<5"

# -------------------------------
# Runtime stage
# -------------------------------
FROM python:3.13-slim AS runtime

# Enable fail-fast in runtime stage too
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Install runtime packages
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for app (create early)
RUN useradd -m -u 10001 llamacrawl

WORKDIR /app

# Copy virtual environment from builder (set ownership during copy - FAST)
COPY --from=builder --chown=llamacrawl:llamacrawl /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application assets (set ownership during copy - FAST)
COPY --chown=llamacrawl:llamacrawl apps/api ./apps/api
COPY --from=packages --chown=llamacrawl:llamacrawl . ./packages
# Contract definitions required by shared packages (e.g., Neo4j/Qdrant schema loaders)
COPY --chown=llamacrawl:llamacrawl specs ./specs

# Switch to non-root user
USER llamacrawl

EXPOSE 8000

# Health check: verify FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "apps.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
