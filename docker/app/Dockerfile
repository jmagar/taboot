# syntax=docker/dockerfile:1.7-labs

# -------------------------------
# Builder image
# -------------------------------
FROM python:3.13-slim AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_FRONTEND=noninteractive
ARG NODE_MAJOR=20

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

# Install Node.js 20.x LTS
RUN apt-get update && \
    curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - && \
    apt-get install -y --no-install-recommends nodejs=20.* && \
    npm install -g pnpm@10.4.1 && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast, reproducible installs
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Copy only dependency manifests for better layer caching
COPY pyproject.toml uv.lock* ./

# Install Python dependencies (core packages only, full sync happens in runtime after copying source)
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
      slowapi \
      pyjwt \
      python-json-logger \
      pydantic-settings

# Copy Node.js workspace files for web app
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./

# Copy all packages-ts and apps/web source (needed for workspace resolution)
COPY packages-ts ./packages-ts
COPY apps/web ./apps/web

# Install Node.js dependencies with frozen lockfile for deterministic builds
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# Build Next.js production bundle
RUN pnpm --filter @taboot/web build

# -------------------------------
# Runtime image
# -------------------------------
FROM python:3.13-slim AS runtime

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG NODE_MAJOR=20

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app

# Non-root user for app
RUN useradd -m -u 10001 llamacrawl

# Minimal runtime packages + Node.js + supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x LTS (runtime only)
RUN apt-get update && \
    curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - && \
    apt-get install -y --no-install-recommends nodejs=20.* && \
    npm install -g pnpm@10.4.1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed site-packages and entrypoints from builder
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /root/.local/bin/ /root/.local/bin/

# Copy Python application code
COPY apps ./apps
COPY packages ./packages
COPY README.md pyproject.toml uv.lock ./

# Copy standalone Next.js app (optimized output with minimal dependencies)
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public

# Install Python workspace dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Copy supervisord config
COPY docker/app/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create log directories for supervisor
RUN mkdir -p /var/log/supervisor && chmod 755 /var/log/supervisor

# Create a writable home for SSH mounts (from compose)
RUN mkdir -p /home/llamacrawl/.ssh && chown -R llamacrawl:llamacrawl /home/llamacrawl

# Note: supervisord runs as root to manage processes, but apps run as llamacrawl user

EXPOSE 8000 3000

# Health check: verify both FastAPI (8000) and Next.js (3000) are responding
# Checks API /health endpoint first, falls back to Next.js /api/test endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || curl -f http://localhost:3000/api/test || exit 1

# Run both API and web via supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
