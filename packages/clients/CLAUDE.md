See @../../CLAUDE.md for repository-wide conventions.

# Clients Guidance

- Treat this directory as generated code. Do not hand-edit outputs—update
  generation scripts instead.
- Keep Python artifacts under `python/`, TS under `typescript/`, and store
  generators/helpers in `scripts/`.
- Regenerate clients whenever the API schema changes. Coordinate with
  `packages/schemas` and `apps/api` to keep contracts in sync.
- Avoid importing these clients from runtime services (API/worker). They are
  intended for external consumers or integration tests.

# Testing & Quality

- Smoke test generated clients after regeneration (e.g. basic auth / request
  flows) before committing.
- Run linters/formatters appropriate to the generated languages if the generator
  supports it.
