<!--
Sync Impact Report:
- Version change: N/A (new) → 1.0.0
- New constitution created from template
- Added principles:
  1. Type-Safe Architecture (no any type, mypy strict mode)
  2. Fail-Fast Error Handling (throw early, no fallbacks)
  3. Test-Driven Development (≥85% core coverage, TDD mandatory)
  4. Layered Dependency Flow (apps → adapters → core)
  5. Performance First (quantified targets per tier)
- Added sections:
  - Quality Gates (compliance checkpoints)
  - Development Standards (tooling and conventions)
- Templates requiring updates:
  ✅ Updated - N/A (initial creation)
- Follow-up TODOs: None
-->

# LlamaCrawl v2 Constitution

## Core Principles

### I. Type-Safe Architecture

All code MUST use strict type hints with zero `any` types. Mypy runs in strict mode with no exclusions. Look up actual types from library documentation rather than guessing or using escape hatches. Pre-production status means no fallbacks—type errors MUST be fixed, not suppressed.

**Rationale:** Type safety catches integration bugs at compile time, prevents runtime surprises in graph/vector adapters, and ensures contract clarity across the apps → adapters → core boundary.

### II. Fail-Fast Error Handling

Throw errors early and often. NEVER use fallbacks, default values, or silent error suppression. If data is invalid, the system MUST halt immediately with a clear error message indicating the problem and location.

**Rationale:** Pre-production codebase optimizes for debuggability and correctness. Silent failures obscure root causes; explicit failures expose issues immediately during development, preventing compounding errors in downstream components.

### III. Test-Driven Development (NON-NEGOTIABLE)

**All new code MUST follow Red-Green-Refactor cycle:**
1. Write failing test first (Red phase)
2. Write minimal code to pass (Green phase)
3. Refactor for clarity (Refactor phase)

**Specific requirements:**
- Unit and integration tests MUST be written before implementation
- Target: ≥85% coverage in `packages/core` and extraction logic
- Tests mirror `tests/<package>/<module>/test_*.py` structure
- Markers: `unit`, `integration`, `slow`, plus source-specific (`gmail`, `github`, `reddit`, `elasticsearch`, `firecrawl`)
- Full integration tests require Docker services healthy
- Use lightweight fixtures over static payloads

**Extraction Quality Gates:**
- F1 score guardrails: CI fails if F1 drops ≥2 points
- Labeled validation set: ~300 windows minimum before tier changes merge
- Tier performance benchmarks: Must meet target throughput in CI

**Rationale:** TDD ensures testable design, prevents regressions, and guarantees extraction/retrieval logic meets precision requirements. Given early project stage (5% implementation), TDD discipline catches architectural issues before 5k LOC implementation accumulates technical debt.

### IV. Explicit Dependency Declaration & Layered Flow

**Strict dependency direction:** `apps → adapters → core`

- **`packages/core/`:** Business logic, domain models, ports (interfaces). No framework dependencies. Depends only on `packages/schemas` and `packages/common`.
- **Adapter packages:** Pluggable implementations (`ingest`, `extraction`, `graph`, `vector`, `retrieval`, `schemas`, `common`). Each has explicit `pyproject.toml` with declared dependencies.
- **App shells:** Thin I/O layers (`apps/api`, `apps/cli`, `apps/mcp`, `apps/web`). Apps NEVER contain business logic. Each has explicit `pyproject.toml`.

**Dependency Materialization Rules:**
- Every `packages/<adapter>/` MUST have its own `pyproject.toml` with explicit dependencies
- No implicit transitive dependencies via another package
- All third-party libraries must be explicitly declared (even if brought in by another package)
- Adapters can depend on their specific framework (`neo4j`, `qdrant_client`, `llama_index`, etc.)

Enforced via: `uv sync` (workspace validation), `import-linter` (Python), and CI import audits.

**Rationale:** Layered architecture ensures core business logic remains framework-agnostic, testable, and replaceable. Apps serve as minimal adapters between external interfaces. Explicit dependencies prevent implicit transitive coupling and enable clear adapter substitution.

### V. Performance First (Expanded)

Quantified performance targets (RTX 4070):

- **Tier A extraction:** ≥50 pages/sec (CPU)
- **Tier B extraction:** ≥200 sentences/sec (`en_core_web_md`), ≥40 (`trf`)
- **Tier C extraction:** median ≤250ms/window, p95 ≤750ms (batched 8–16)
- **Neo4j writes:** ≥20k edges/min (2k-row UNWIND batches)
- **Qdrant upserts:** ≥5k vectors/sec (768-dim, HNSW)
- **E2E query latency:** p95 <3 seconds (search + rerank + synthesis)

**Regression Policy:**
- Benchmarks run on every commit (CI gate)
- Regressions >5% block merge
- New features must include perf test or measurement
- Monthly performance audit against baseline

**Profiling Requirement:**
All new performance-critical code (extraction tiers, graph writers, retrievers) MUST include:
- Flame graph or profiler output in PR
- Latency/throughput measurement
- Comparison vs. targets

**Rationale:** RAG platform value depends on ingestion speed and retrieval latency. Explicit targets and regression policy prevent performance erosion and guide optimization efforts.

### VI. Framework Isolation (Core Layer)

The `packages/core/` layer MUST have ZERO framework dependencies. Core can only import from:
- Standard library (`typing`, `dataclasses`, `abc`, `enum`, `datetime`, `uuid`)
- `packages.schemas` (Pydantic models)
- `packages.common` (logging, config, utilities)

**Prohibited in core:** `llama_index`, `fastapi`, `typer`, `neo4j`, `qdrant_client`, `firecrawl`, `playwright`

Verified via: `import-linter` configuration + code review checklist.

**Rationale:** Core business logic must remain testable, replaceable, and independent of any particular framework. This enables:
- Framework migration without rewriting core
- Isolated unit testing without Docker
- Adapter substitution for testing/alternate implementations
- Clear contract definition via ports/interfaces

### VII. Observability & Validation

- **Metrics:** windows/sec, tier hit ratios, LLM p95, cache hit-rate, DB throughput.
- **Tracing:** Chain `doc_id → section → windows → triples → Neo4j txId`.
- **Validation:** ~300 labeled windows with F1 guardrails; CI fails if F1 drops ≥2 points.
- **Logging:** JSON structured via `python-json-logger`.

Every component MUST expose structured logs and metrics. Extraction quality MUST be validated against labeled datasets before merging.

**Rationale:** Production-grade systems require observability to diagnose failures, optimize performance, and verify correctness. F1 guardrails prevent silent quality degradation.

### VIII. Extraction Pipeline Contracts

The multi-tier extraction system MUST maintain these invariants:

**Tier A (Deterministic):** All outputs cached, reproducible, 0 latency variance
- No LLM calls, no ML model inference
- Regex/JSON/YAML parsing only
- Must complete ≥50 pages/sec on CPU

**Tier B (spaCy NLP):** Stateless, reproducible with fixed seed, GPU-optional
- Entity ruler + dependency matchers only
- No LLM calls
- Must complete ≥200 sentences/sec (md) or ≥40 (trf)

**Tier C (LLM Windows):** Cacheable, temperature=0, JSON schema validation
- Redis cache keyed by window hash
- Ollama Qwen3-4B-Instruct only (no GPT/Claude API)
- Batched 8–16 windows; median ≤250ms, p95 ≤750ms

**No tier may skip/bypass lower tiers.** Every document flows: Tier A → Tier B → Tier C.

**Rationale:** Explicit tier contracts prevent implementation shortcuts that degrade pipeline quality and latency.

## Quality Gates

All pull requests MUST pass these gates before merge:

1. **Linting & Formatting:** Ruff (Python), ESLint + Prettier (TypeScript). No warnings.
2. **Type Checking:** Mypy strict mode (Python), TypeScript strict mode. Zero errors.
3. **Tests:** All tests pass; ≥85% coverage in `packages/core` and extraction logic.
4. **Performance:** Benchmarks meet targets; no regressions >5%.
5. **F1 Validation:** Extraction quality on labeled dataset maintains F1 score (no drop ≥2 points).
6. **Integration Health:** Docker services healthy before integration tests run.

## Development Standards

### Code Style & Conventions

- **Line length:** 100 characters (enforced by Ruff).
- **Python naming:** modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- **Adapters:** Name for their system (`neo4j_writer.py`, `qdrant_client.py`).
- **Type hints:** All functions annotated; never use bare `any` type.
- **Imports:** Ruff auto-formats; respect layering rules (no reverse imports).

### Tooling

- **Python:** `uv` workspace, Ruff, Mypy, Pytest.
- **JS/TS:** `pnpm` + Turborepo, ESLint, Vitest/Playwright.
- **Pre-commit:** Ruff/Black/Mypy + ESLint/Prettier.
- **CI (GitHub Actions):** lint, typecheck, test, build, dockerize `api`/`mcp`; cache `uv` + `pnpm` + turbo.

### Commits & Pull Requests

- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`.
- Keep commits focused on a single concern.
- Note executed test command in PR body.
- Request reviewers for cross-layer work (core + adapters).
- Link related issues or docs.

## Implementation Phases (MVP Roadmap)

This constitution governs all 8 phases of LlamaCrawl v2 implementation:

**Phase 1 (Weeks 1–2): Core Layer**
- Implement `packages/core/` domain models, ports, value objects
- Establishes all domain contracts
- Must pass mypy strict, ≥85% test coverage

**Phase 2 (Weeks 3–4): Ingestion Pipeline**
- Implement `packages/ingest/` (normalizer, chunker, Firecrawl integration)
- First API endpoint: `POST /api/ingest`
- Must pass performance target ≥5k vectors/sec into Qdrant

**Phase 3 (Weeks 5–6): Extraction Tier A**
- Implement deterministic extractors (regex, JSON, YAML)
- Must pass target ≥50 pages/sec

**Phase 4–5 (Weeks 7–10): Extraction Tiers B & C**
- Implement spaCy (Tier B) and Ollama LLM (Tier C)
- Targets: ≥200 sentences/sec, ≤250ms median/window
- Enable `taboot-worker` container

**Phase 6 (Weeks 11): Retrieval Pipeline**
- Wire 6-stage retrieval (embed → search → rerank → traverse → synthesize)
- Query endpoint: `POST /api/query`
- Add citation generation

**Phase 7 (Week 12): CLI & MCP**
- Implement CLI commands and MCP handlers
- Cover: ingest, extract, query, status, list workflows

**Phase 8 (Weeks 13–14): Test Suite & Tuning**
- Full integration tests (≥85% coverage)
- Performance optimization to meet all targets
- F1 score validation on labeled dataset (≥0.90)

Each phase MUST maintain compliance with all constitution principles.

## Pre-Production Status (Temporary Relaxations)

While in pre-production (phases 1–8), the following relaxations apply:

1. **No data migrations required** — Can break schema between commits (no backward compatibility needed)
2. **No API versioning** — Single API version; clients must track `main` branch
3. **Can refactor liberally** — Breaking changes allowed; deprecation cycles not required
4. **Experimental features allowed** — Can merge experimental code behind feature flags if ≥85% test coverage maintained

**Production Transition Checklist (When Applying Constitution to Prod):**
- [ ] All tests at ≥85% coverage
- [ ] All performance targets met consistently (3-run median)
- [ ] Extraction F1 score validated at ≥0.90 on labeled dataset
- [ ] Observability (metrics, traces, logs) production-ready
- [ ] Security audit completed (credential handling, input validation)
- [ ] Schema stability: first schema version frozen and documented
- [ ] API versioning established; v1 released
- [ ] Data governance and retention policies enacted

## Governance

This constitution supersedes all other practices. Amendments require:

1. Documentation of rationale and impact analysis.
2. Approval from project maintainers.
3. Migration plan if principle change affects existing code.

All PRs and code reviews MUST verify compliance with these principles. Complexity MUST be justified; simplicity is the default. Use `CLAUDE.md` for runtime development guidance specific to Claude Code.

**Version**: 2.0.0 | **Ratified**: 2025-10-20 | **Last Amended**: 2025-10-20 (Phase 1 Implementation Focus)
