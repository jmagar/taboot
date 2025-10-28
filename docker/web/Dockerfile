# syntax=docker/dockerfile:1.7-labs

# -------------------------------
# Base stage - setup pnpm and turbo
# -------------------------------
FROM node:22-alpine AS base

# Enable fail-fast: exit immediately on error, fail on pipe errors, fail on undefined variables
SHELL ["/bin/sh", "-euo", "pipefail", "-c"]

# Install system dependencies and package managers
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

RUN set -eux; \
    apk update && apk upgrade && apk add --no-cache libc6-compat \
    && npm install -g pnpm@10.4.1 \
    && pnpm config set global-bin-dir "$PNPM_HOME" \
    && pnpm add -g turbo@2.3.3

# -------------------------------
# Development stage (optional, for local dev with Docker)
# -------------------------------
FROM base AS development

WORKDIR /app

# Copy workspace configuration
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY turbo.json ./

# Copy all packages and apps for development
COPY packages-ts ./packages-ts
COPY apps/web ./apps/web

# Install all dependencies (including dev)
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    set -eux; \
    pnpm install --frozen-lockfile

EXPOSE 3000
CMD ["pnpm", "--filter", "@taboot/web", "dev"]

# -------------------------------
# Builder stage - prune workspace for web app
# -------------------------------
FROM base AS builder

WORKDIR /app

# Copy web app and workspace files
COPY apps/web ./apps/web
COPY --from=packages-ts . ./packages-ts
# Copy workspace config from web context
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json turbo.json ./

# Prune workspace to only include @taboot/web and its dependencies
RUN turbo prune @taboot/web --docker

# -------------------------------
# Installer stage - install deps and build
# -------------------------------
FROM base AS installer

WORKDIR /app

# Copy pruned workspace from builder (only the pruned package.json files)
COPY --from=builder /app/out/json ./

# Install all dependencies (needed for build)
# Note: pnpm install will create proper lockfile with all transitive dependencies
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    set -eux; \
    pnpm install --ignore-scripts || { echo "ERROR: pnpm install failed"; exit 1; }

# Copy source files and build configuration
COPY --from=builder /app/out/full ./

# Generate Prisma client (required before build)
# Cache Prisma engines and retry on network failure
RUN --mount=type=cache,target=/tmp/prisma-engines \
    set -eux; \
    export PRISMA_ENGINES_CACHE_DIR=/tmp/prisma-engines \
    && export PRISMA_CLI_BINARY_TARGETS="linux-musl-openssl-3.0.x" \
    && for i in 1 2 3; do \
        pnpm --filter @taboot/db db:generate && break || \
        (echo "Prisma generate attempt $i failed, retrying..." && sleep 5); \
    done \
    || { echo "ERROR: Prisma generation failed after 3 attempts"; exit 1; }

# Build Next.js app with turbo (standalone output)
RUN set -eux; \
    turbo build --filter=@taboot/web || { echo "ERROR: Build failed"; exit 1; }

# -------------------------------
# Production stage - minimal runtime
# -------------------------------
FROM node:22-alpine AS production

# Install curl for health checks and libc6-compat for compatibility
RUN apk update && apk upgrade && apk add --no-cache curl libc6-compat

WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy standalone Next.js build
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

# Validate server.js exists in standalone build
RUN test -f apps/web/server.js || { echo "ERROR: server.js not found in standalone build - check Next.js output structure"; exit 1; }

# Switch to non-root user
USER nextjs

EXPOSE 3000

ENV NODE_ENV=production \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

# Configurable healthcheck endpoint (default: /api/health)
ENV HEALTHCHECK_PATH=/api/health
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:3000${HEALTHCHECK_PATH}" || exit 1

# Run Next.js standalone server
CMD ["node", "apps/web/server.js"]
