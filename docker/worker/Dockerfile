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

# Install dependencies into virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Install pip into the virtual environment for spaCy model download
RUN uv pip install --python /app/.venv/bin/python pip

# Download spaCy model using the virtual environment Python
RUN /app/.venv/bin/python -m spacy download en_core_web_md

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
    PYTHONPATH=/app

# hadolint ignore=DL3008  # rely on latest security patches, see docs/docker/README.md
# Install minimal runtime packages (unpinned to receive security updates with base image)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only virtual environment from builder (NOT entire Python installation)
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --from=builder /app/apps ./apps
COPY --from=builder /app/packages ./packages
COPY --from=builder /app/README.md /app/pyproject.toml /app/uv.lock ./

# Create non-root user and set ownership
RUN useradd -m -u 10002 taboot && chown -R taboot:taboot /app

USER taboot

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "-m", "apps.worker.main"]
