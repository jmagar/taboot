See @../../CLAUDE.md for repository-wide conventions.

# CLI App Guidance

- Commands belong in `apps/cli/commands/` (mirroring Typer subcommands). Keep
  them thin—resolve inputs, call `packages.core` use-cases, format output.
- Reuse shared DTOs from `packages.schemas` instead of redefining models.
- Shared utilities (prompting, output formatting) should live under
  `apps/cli/services/` or similar helper modules once created.
- Respect environment configuration documented in `docs/CONFIGURATION.md`. Use
  `uv run --env-file .env …` in examples and docs.
- Document new commands in this README and provide usage examples accessible via
  Typer's help system.

# Testing & Quality

- Add coverage under `tests/cli/` mirroring command modules. Focus on argument
  parsing, integration with core use-cases, and error handling.
- Run `uv run pytest tests/cli -m "not slow"`, `uv run ruff check apps/cli`, and
  `uv run mypy apps/cli` before submitting changes.
- Update CLI help output (Typer docstrings) whenever command signatures change.
