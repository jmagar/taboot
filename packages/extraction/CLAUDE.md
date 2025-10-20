See @../../CLAUDE.md for repository-wide conventions.

# Extraction Package Guidance

- Follow the tiered architecture: Tier A (deterministic), Tier B (spaCy),
  Tier C (LLM windows). Keep implementations in their respective subpackages.
- Orchestrate tiers via pipeline modules—avoid tight coupling so single tiers
  can be rerun or replaced independently.
- Use shared schemas from `packages.schemas` and ports from `packages.core` for
  output.
- Implement caching/versioning per `EXTRACTION_SPEC.md` (e.g., Redis window cache,
  extractor version stamps).
- Monitor performance metrics and expose them through `packages.common`
  observability helpers.

# Testing & Quality

- Add tests under `tests/extraction/` for tier-specific behaviour and pipeline
  integration. Include fixtures near their usage.
- Run `uv run pytest tests/extraction -m "not slow"`, `uv run ruff check packages/extraction`,
  and `uv run mypy packages/extraction` before submitting changes.
- Update `packages/extraction/docs/EXTRACTION_SPEC.md` when adding new extractor
  strategies or altering expected outputs.
