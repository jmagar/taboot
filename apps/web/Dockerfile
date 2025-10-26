# syntax=docker/dockerfile:1.7-labs

# -------------------------------
# Base stage - setup pnpm and turbo
# -------------------------------
FROM node:22-alpine AS base

# Install pnpm and turbo globally
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate \
    && npm install -g turbo@2.3.3

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
    pnpm install --frozen-lockfile

EXPOSE 3000
CMD ["pnpm", "--filter", "@taboot/web", "dev"]

# -------------------------------
# Builder stage - prune workspace for web app
# -------------------------------
FROM base AS builder

WORKDIR /app

# Prune workspace to only include @taboot/web and its dependencies
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY turbo.json ./
RUN turbo prune @taboot/web --docker

# -------------------------------
# Installer stage - install deps and build
# -------------------------------
FROM base AS installer

WORKDIR /app

# Copy pruned workspace from builder
COPY --from=builder /app/out/json ./
COPY --from=builder /app/out/pnpm-lock.yaml ./pnpm-lock.yaml
COPY --from=builder /app/out/pnpm-workspace.yaml ./pnpm-workspace.yaml

# Install production dependencies only
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile --prod

# Copy source files and build configuration
COPY --from=builder /app/out/full ./

# Generate Prisma client (required before build)
RUN pnpm --filter @taboot/db prisma:generate

# Build Next.js app with turbo (standalone output)
RUN turbo build --filter=@taboot/web

# -------------------------------
# Production stage - minimal runtime
# -------------------------------
FROM node:22-alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy standalone Next.js build
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

# Switch to non-root user
USER nextjs

EXPOSE 3000

ENV NODE_ENV=production \
    PORT=3000

# Health check: verify Next.js /api/health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://127.0.0.1:3000/api/health || exit 1

# Run Next.js standalone server
CMD ["node", "apps/web/server.js"]
