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

# Install Node.js 20.x LTS
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm@9

# Install uv for fast, reproducible installs
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Copy only dependency manifests for better layer caching
COPY pyproject.toml uv.lock* ./

# Install Python dependencies
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
      slowapi

# Copy Node.js workspace files for web app
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./

# Copy all packages-ts and apps/web source (needed for workspace resolution)
COPY packages-ts ./packages-ts
COPY apps/web ./apps/web

# Install Node.js dependencies (no-frozen-lockfile for Docker build)
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --no-frozen-lockfile

# Build Next.js production bundle
RUN pnpm --filter @taboot/web build

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

# Minimal runtime packages + Node.js + supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x LTS (runtime only)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm@9 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed site-packages and entrypoints from builder
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /root/.local/bin/ /root/.local/bin/

# Copy Python application code
COPY apps ./apps
COPY packages ./packages
COPY README.md pyproject.toml uv.lock ./

# Copy Node.js dependencies and built web app from builder
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/apps/web ./apps/web
COPY --from=builder /app/packages-ts ./packages-ts
COPY --from=builder /app/pnpm-workspace.yaml /app/pnpm-lock.yaml /app/package.json ./

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

# Healthcheck is handled by docker-compose (both API and web)

# Run both API and web via supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
