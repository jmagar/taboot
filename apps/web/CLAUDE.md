See @../../CLAUDE.md for repository-wide conventions.

# Web App Guidance

- Use Next.js conventions: pages under `apps/web/pages/`, shared UI in
  `apps/web/components/`, and domain-specific modules in `apps/web/features/`.
- Consume API data via generated clients in `packages/clients`. Keep schemas in
  sync with `packages/schemas`.
- Store API base URLs in environment variables (`NEXT_PUBLIC_API_URL`). Avoid
  embedding constants.
- Follow the design system / component guidelines as they land (add a section
  once the design system repo is referenced).
- Keep server-side logic minimal; rely on API endpoints for business logic.

# Testing & Quality

- Add unit/integration tests under `apps/web/tests/` once scaffolded.
- Run `pnpm lint --filter web`, `pnpm test --filter web`, and `pnpm build --filter web`
  before submitting changes.
- Update documentation (`apps/web/README.md`) whenever you add new workflows or
  environment requirements.
