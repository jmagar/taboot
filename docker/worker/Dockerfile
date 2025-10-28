# syntax=docker/dockerfile:1.7-labs

# -------------------------------
# Builder image
# -------------------------------
FROM python:3.11-slim AS builder

# Enable fail-fast: exit immediately on error, fail on pipe errors, fail on undefined variables
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      git \
      ca-certificates \
      libpq-dev \
      pkg-config \
      python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python -m venv /opt/worker-venv
ENV PATH="/opt/worker-venv/bin:$PATH"
RUN pip install --upgrade pip

# Copy minimal application code required by worker runtime
COPY apps/worker ./apps/worker
COPY packages ./packages
COPY specs ./specs
COPY pyproject.toml uv.lock README.md ./

# Install workspace-specific packages (LlamaIndex, clients, etc.) into worker venv
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
      "llama-index-core>=0.14.4,<1" \
      "llama-index-vector-stores-qdrant>=0.8.6,<1" \
      "llama-index-graph-stores-neo4j>=0.5.1,<1" \
      "llama-index-llms-ollama>=0.3.0,<1" \
      "llama-index-embeddings-huggingface>=0.3.0,<1" \
      "qdrant-client>=1.15.1,<2" \
      "neo4j>=5.26.0,<6" \
      "redis>=5.0.1,<6" \
      "firecrawl-py>=4.4.0,<5" \
      "pydantic>=2.12.0,<3" \
      "pydantic-settings>=2.7.0,<3" \
      "python-dotenv>=1.1.1,<2" \
      "python-json-logger>=4.0.0,<5" \
      "pyyaml>=6.0.3,<7" \
      "psycopg2-binary>=2.9.11,<3" \
      "httpx>=0.28.1,<1"

# -----------------------------------------------
# Runtime image
# -----------------------------------------------
FROM python:3.11-slim AS runtime

# Enable fail-fast in runtime stage too
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# hadolint ignore=DL3008  # rely on latest security patches, see docs/docker/README.md
# Install minimal runtime packages (unpinned to receive security updates with base image)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user early
RUN useradd -m -u 10002 taboot

WORKDIR /app

# Copy ML venv with workspace packages from builder (set ownership during copy - FAST)
COPY --from=builder --chown=taboot:taboot /opt/worker-venv /opt/worker-venv
ENV PATH="/opt/worker-venv/bin:$PATH"

# Copy application code (set ownership during copy - FAST)
COPY --from=builder --chown=taboot:taboot /app/apps ./apps
COPY --from=builder --chown=taboot:taboot /app/packages ./packages
COPY --from=builder --chown=taboot:taboot /app/specs ./specs
COPY --from=builder --chown=taboot:taboot /app/README.md /app/pyproject.toml /app/uv.lock ./

USER taboot

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "apps.worker.main" > /dev/null || exit 1

CMD ["python", "-m", "apps.worker.main"]
