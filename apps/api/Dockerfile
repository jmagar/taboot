# syntax=docker/dockerfile:1.7-labs

# -------------------------------
# Builder stage
# -------------------------------
FROM python:3.13-slim AS builder

# Enable fail-fast: exit immediately on error, fail on pipe errors
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

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

# Copy dependency manifests
COPY pyproject.toml uv.lock* README.md ./

# Install Python dependencies with cache
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# -------------------------------
# Runtime stage
# -------------------------------
FROM python:3.13-slim AS runtime

# Enable fail-fast in runtime stage too
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app

# Non-root user for app
RUN useradd -m -u 10001 llamacrawl

# Install runtime packages
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed site-packages and entrypoints from builder
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /root/.local/bin/ /root/.local/bin/

# Copy application assets
COPY apps ./apps
COPY packages ./packages
COPY README.md pyproject.toml uv.lock ./

# Setup runtime directories and permissions
RUN mkdir -p /home/llamacrawl \
    && chown -R llamacrawl:llamacrawl /home/llamacrawl /app

# Switch to non-root user
USER llamacrawl

EXPOSE 8000

# Health check: verify FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "apps.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
