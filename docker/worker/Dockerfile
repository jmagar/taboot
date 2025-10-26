# syntax=docker/dockerfile:1.7-labs

# -------------------------------
# Builder image
# -------------------------------
FROM python:3.13-slim AS builder

# Enable fail-fast: exit immediately on error, fail on pipe errors
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app

ARG DEBIAN_FRONTEND=noninteractive

# Install build dependencies and uv in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      git \
      ca-certificates \
      libpq-dev \
      pkg-config \
      python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests
COPY pyproject.toml uv.lock README.md ./

# Install dependencies and download spaCy model
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev \
    && python -m spacy download en_core_web_md

# Copy application code
COPY apps ./apps
COPY packages ./packages

# -----------------------------------------------
# Runtime image
# -----------------------------------------------
FROM python:3.13-slim AS runtime

# Enable fail-fast in runtime stage too
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app

# Install minimal runtime packages
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /root/.local/bin/ /root/.local/bin/
COPY --from=builder /root/.cache /root/.cache

# Copy application code
COPY apps ./apps
COPY packages ./packages
COPY README.md pyproject.toml uv.lock ./

# Create non-root user and set ownership
RUN useradd -m -u 10002 taboot && chown -R taboot:taboot /app

USER taboot

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["uv", "run", "python", "-m", "apps.worker.main"]

