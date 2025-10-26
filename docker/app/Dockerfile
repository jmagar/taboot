# syntax=docker/dockerfile:1.7-labs

# -------------------------------
# Builder image
# -------------------------------
FROM python:3.13-slim AS builder

# Enable fail-fast: exit immediately on error, fail on pipe errors
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

ARG DEBIAN_FRONTEND=noninteractive
ARG NODE_MAJOR=20

# System dependencies for building Python wheels and Node.js apps
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      git \
      curl \
      ca-certificates \
      libpq-dev \
      pkg-config \
      python3-dev \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs=20.* \
    && npm install -g pnpm@10.4.1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, reproducible installs
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests
COPY pyproject.toml uv.lock* README.md ./
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./

# Install Python dependencies with cache
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Copy source code for Next.js build
COPY packages-ts ./packages-ts
COPY apps/web ./apps/web

# Install Node.js dependencies and build production bundle
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile \
    && pnpm --filter @taboot/web build

# -------------------------------
# Runtime image
# -------------------------------
FROM python:3.13-slim AS runtime

# Enable fail-fast in runtime stage too
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

ARG NODE_MAJOR=20

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app

# Non-root user for app
RUN useradd -m -u 10001 llamacrawl

# Install runtime packages (Node.js + supervisor)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      supervisor \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs=20.* \
    && npm install -g pnpm@10.4.1 \
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
COPY docker/app/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy Next.js standalone build
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public

# Setup runtime directories and permissions
RUN mkdir -p /var/log/supervisor /home/llamacrawl/.ssh \
    && chmod 755 /var/log/supervisor \
    && chown -R llamacrawl:llamacrawl /home/llamacrawl

EXPOSE 8000 3000

# Health check: verify both FastAPI (8000) and Next.js (3000) are responding
# Checks API /health endpoint first, falls back to Next.js /api/test endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || curl -f http://localhost:3000/api/test || exit 1

# Run both API and web via supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
