# Packages / Common

Shared utilities for logging, configuration, tracing, and other cross-cutting
concerns. Everything here should be framework-agnostic and safe to import from
apps, adapters, and core.

## Layout

```
packages/common/
├── README.md
├── logging/           # Structured logging helpers / formatters
├── config/            # Environment/config loaders
├── observability/     # Metrics/tracing helpers
├── utils/             # Misc support utilities
└── __init__.py
```

Populate subpackages as they come online. Keep modules cohesive so downstream
packages can depend on specific functionality without pulling unnecessary code.

## Key docs

- [`docs/CONFIGURATION.md`](../../docs/CONFIGURATION.md) – environment variables
  surfaced by configuration loaders.
- [`apps/api/docs/OBSERVABILITY.md`](../../apps/api/docs/OBSERVABILITY.md) – logging
  and metrics expectations that this package should help satisfy.

## Guidelines

- No business logic—only reusable helpers.
- Avoid dependency on FastAPI, Typer, etc. Use standard library or minimal
  third-party packages.
- Keep logging defaults aligned with the structured JSON format described in
  observability docs (request IDs, job IDs, elapsed ms).
- When adding new configuration helpers, update `docs/CONFIGURATION.md` with the
  expected environment variables and defaults.
