# Taboot Web - Next.js Multi-stage Dockerfile
# Based on build-elevate template with Taboot-specific adaptations

FROM node:22-alpine AS base

# Development stage - used for local development with hot reload
FROM base AS development

ARG PNPM_VERSION=9.12.3
ARG TURBO_VERSION=2.1.3

RUN apk update && apk upgrade
RUN apk add --no-cache libc6-compat

# Install pnpm and configure PNPM_HOME
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

RUN corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate && \
    pnpm config set global-bin-dir "$PNPM_HOME"

WORKDIR /app

# Copy package files for dependency installation
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY packages-ts/ ./packages-ts/
COPY apps/web/package.json ./apps/web/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy application code
COPY apps/web/ ./apps/web/

# Expose Next.js dev server port
EXPOSE 3000

# Development command (overridden by docker-compose)
CMD ["pnpm", "dev", "--filter", "@taboot/web"]

# Builder stage - builds the production application
FROM base AS builder

ARG PNPM_VERSION=9.12.3
ARG TURBO_VERSION=2.1.3

RUN apk update && apk upgrade
RUN apk add --no-cache libc6-compat

# Install pnpm and Turborepo
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

RUN corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate && \
    pnpm config set global-bin-dir "$PNPM_HOME"

WORKDIR /app

# Copy entire workspace for Turbo prune
COPY . .

# Prune workspace to only web app dependencies
RUN pnpm dlx turbo@${TURBO_VERSION} prune @taboot/web --docker

# Installer stage - installs dependencies and builds
FROM base AS installer

ARG PNPM_VERSION=9.12.3
ARG TURBO_VERSION=2.1.3

RUN apk update && apk upgrade
RUN apk add --no-cache libc6-compat

ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

RUN corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate && \
    pnpm config set global-bin-dir "$PNPM_HOME"

WORKDIR /app

# Install dependencies from pruned workspace
COPY --from=builder /app/out/json/ .
RUN pnpm install --frozen-lockfile --ignore-scripts

# Copy application source
COPY --from=builder /app/out/full/ .

# Generate Prisma client (if db package exists)
RUN pnpm --filter @taboot/db db:generate || echo "No Prisma schema found, skipping..."

# Build the application with Turbo
RUN pnpm dlx turbo@${TURBO_VERSION} build --filter=@taboot/web

# Production runner stage
FROM base AS production
WORKDIR /app

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs
USER nextjs

# Copy built application using Next.js output tracing
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD node -e "require('http').get('http://127.0.0.1:3000/api/health',r=>{process.exit(r.statusCode===200?0:1)}).on('error',()=>process.exit(1))"

CMD ["node", "apps/web/server.js"]
