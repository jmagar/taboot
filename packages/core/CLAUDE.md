See @../../CLAUDE.md for repository-wide conventions.

# Core Package Guidance

- Core is the single source of truth for business logic. It may only depend on
  `packages.schemas` and `packages.common`.
- Define ports under `packages/core/ports/` for any external interaction.
  Adapters implement these ports in their respective packages.
- Use cases orchestrate domain behaviour; keep them pure (no framework details)
  and parameterize dependencies via ports.
- Entities/value objects should enforce invariants and domain rules; prefer
  immutable structures when possible.

# Testing & Quality

- Place tests under `tests/core/` mirroring the package structure. Aim for high
  coverage (≥85 %) as per project guidelines.
- Run `uv run pytest tests/core -m "not slow"`, `uv run ruff check packages/core`,
  and `uv run mypy packages/core` when touching this package.
- Document meaningful domain changes in project docs (architecture,
  lifecycle runbooks) so other layers stay in sync.
