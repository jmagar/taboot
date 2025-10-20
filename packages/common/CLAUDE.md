See @../../CLAUDE.md for repository-wide conventions.

# Common Package Guidance

- Restrict functionality to reusable utilities (logging, config, tracing,
  helpers). No business logic.
- Keep dependencies minimal. If a helper needs a heavy dependency, reconsider if
  it belongs in an adapter instead.
- Public APIs should be explicitly exported via `packages/common/__init__.py` so
  downstream imports stay stable.
- Document any new environment variables or conventions in
  `docs/CONFIGURATION.md`.

# Testing & Quality

- Place tests in `tests/common/` mirroring module paths.
- Run `uv run pytest tests/common -m "not slow"`, `uv run ruff check packages/common`,
  and `uv run mypy packages/common` when touching this package.
