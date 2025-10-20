# syntax=docker/dockerfile:1.7-labs

# -------------------------------
# Builder image
# -------------------------------
FROM python:3.13-slim AS builder

ARG DEBIAN_FRONTEND=noninteractive

# System deps for building wheels used by spaCy, Neo4j, etc.
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

# Copy only dependency manifests for better layer caching
COPY pyproject.toml uv.lock* ./

# Install key dependencies (skip package install since project structure is incomplete)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --compile-bytecode \
      llama-index-core \
      llama-index-vector-stores-qdrant \
      llama-index-graph-stores-neo4j \
      llama-index-llms-ollama \
      llama-index-embeddings-huggingface \
      firecrawl-py \
      qdrant-client \
      neo4j \
      redis \
      fastapi \
      uvicorn \
      pydantic \
      typer \
      spacy

# -------------------------------
# Runtime image
# -------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app

# Non-root user for app
RUN useradd -m -u 10001 llamacrawl

# Minimal runtime packages (psql client optional for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed site-packages and entrypoints from builder
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code (flat layout, no src/)
COPY apps ./apps
COPY packages ./packages
COPY README.md pyproject.toml ./

# Create a writable home for SSH mounts (from compose)
RUN mkdir -p /home/llamacrawl/.ssh && chown -R llamacrawl:llamacrawl /home/llamacrawl

USER llamacrawl

EXPOSE 8000

# Healthcheck is handled by docker-compose

# Default command; can be overridden by docker-compose
CMD ["uvicorn", "llamacrawl.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
