# Web App

Optional Next.js dashboard for monitoring crawls, ingestion pipelines, and
extraction health. It consumes the public API exposed by `taboot-app`.

## Architecture

- Keep page and layout components under `apps/web/pages/` and feature modules in
  `apps/web/features/` (create directories as we implement them).
- Fetch data via generated clients in `packages/clients`—do not hardcode API
  payload shapes.
- Centralize shared hooks/state in `apps/web/lib/` once scaffolded.

## Setup

```bash
pnpm install                     # once per checkout
pnpm dev --filter web -- --port 5173
```

Set `NEXT_PUBLIC_API_URL` in `.env` so the web client points at the correct
backend (defaults to `http://localhost:8000`). When running inside the compose
stack, the `taboot-app` container injects this value automatically.

## Build & lint

```bash
pnpm lint --filter web
pnpm build --filter web
```

Add component stories, integration tests, and API client hooks in this package.
Generated API clients live under `packages/clients`—import from there rather
than re-declaring schemas.

## Testing

```bash
pnpm test --filter web              # once tests are in place
pnpm lint --filter web
pnpm build --filter web
```

Place Playwright/Storybook/integration suites under `apps/web/tests/`
mirroring component structure when the testing scaffold is added.
