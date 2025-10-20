# syntax=docker/dockerfile:1.7-labs

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app

ARG DEBIAN_FRONTEND=noninteractive

# System dependencies for spaCy and friends
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      git \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for reproducible Python environments
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

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
      spacy \
      pyahocorasick

# Download required spaCy model
RUN python -m spacy download en_core_web_md

# Copy application code
COPY apps ./apps
COPY packages ./packages
COPY README.md pyproject.toml ./

# Non-root user
RUN useradd -m -u 10002 taboot && chown -R taboot:taboot /app

USER taboot

CMD ["uv", "run", "apps/cli", "worker", "start"]

