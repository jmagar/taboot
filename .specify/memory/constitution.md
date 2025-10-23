# Taboot Constitution

## Core Principles

### I. Single-User, Break-Fast Philosophy (NON-NEGOTIABLE)
Taboot is a single-developer system optimized for rapid iteration without backwards compatibility constraints.

**Rules**:
- Breaking changes are acceptable and expected
- No backwards compatibility guarantees
- When in doubt, wipe and rebuild databases
- No migration guides, multi-environment configs, or CONTRIBUTING/SECURITY docs needed
- Optimize for development speed over stability

### II. Strict Architectural Layering
Business logic must be separated from infrastructure through a clean dependency flow: `apps → adapters → core`

**Rules**:
- **Core** (`packages/core/`): Domain models, use-cases, business rules only. No framework dependencies except Pydantic.
- **Adapters** (`packages/{graph,vector,ingest,extraction,retrieval}/`): Framework-specific implementations (Neo4j, Qdrant, LlamaIndex, spaCy)
- **Apps** (`apps/{api,cli,mcp}/`): Thin I/O shells only. No business logic.
- Core may import from adapters directly (no abstract ports pattern needed)
- Apps must never contain business logic - move to core or adapters

### III. Framework-Agnostic Core
Core business logic must remain testable and replaceable without framework coupling.

**Rules**:
- Core never imports `llama_index.*`, `neo4j.*`, `qdrant_client.*`, or other framework code
- Use direct imports from adapter packages when core needs infrastructure (e.g., `from packages.graph.client import Neo4jClient`)
- All external dependencies isolated to adapter packages
- Schemas in `packages/schemas/` define contracts using only Pydantic

### IV. Deterministic-First Extraction
Use deterministic parsing before resorting to LLM-based extraction.

**Rules**:
- **Tier A (Deterministic)**: Regex, YAML/JSON parsing, Aho-Corasick for known patterns. Target ≥50 pages/sec.
- **Tier B (spaCy NLP)**: Entity extraction, dependency parsing. Target ≥200 sentences/sec.
- **Tier C (LLM Windows)**: Only for ambiguous/unstructured content. Qwen3-4B-Instruct, ≤512 tokens, batched. Target ≤250ms median.
- Always try cheaper tiers first, escalate only when necessary

### V. Fail Fast, Throw Early (NON-NEGOTIABLE)
Errors must be caught immediately at the boundary, not deep in execution.

**Rules**:
- Never use fallbacks or silent error handling (we're pre-production)
- Validate inputs at function entry
- Use strict type hints everywhere (`mypy --strict`)
- Never use `any` type - look up actual types
- Break code loudly when refactoring

### VI. Test Coverage Standards
Maintain high confidence in core business logic through testing.

**Rules**:
- Target ≥85% coverage in `packages/core/` and extraction logic
- Unit tests with mocked dependencies for speed
- Integration tests require Docker services healthy
- Markers: `unit`, `integration`, `slow`, source-specific markers
- Test command: `uv run pytest -m "not slow"`

## Technology Stack Requirements

### Mandatory Technologies
- **Python**: 3.11+ managed via `uv`
- **Graph Database**: Neo4j 5.23+ with APOC
- **Vector Database**: Qdrant with GPU acceleration (HNSW indexing)
- **Embeddings**: TEI with Qwen3-Embedding-0.6B
- **Reranking**: SentenceTransformers Qwen3-Reranker-0.6B
- **LLM**: Ollama with Qwen3-4B-Instruct (temperature 0 for extraction)
- **NLP**: spaCy `en_core_web_md` or `trf` models
- **Web Crawling**: Firecrawl v2
- **Retrieval Framework**: LlamaIndex (used across adapter packages: readers in `ingest/`, LLM adapters in `extraction/` Tier C, stores in `vector/` and `graph/`, indices/query engines in `retrieval/`)
- **API Framework**: FastAPI + Typer CLI
- **Orchestration**: Docker Compose with GPU support

### Code Quality Tools (NON-NEGOTIABLE)
- **Linting & Formatting**: Ruff (100 char line length)
- **Type Checking**: mypy in strict mode
- **Testing**: pytest with asyncio support
- **Logging**: JSON structured logs via `python-json-logger`

## Development Workflow

### Pre-Implementation Checklist
1. **Read neighboring files** - understand existing patterns before creating new code
2. **Extend before creating** - modify existing components rather than duplicating
3. **Match conventions** - follow established naming, structure, and import patterns
4. **Use precise types** - research actual types instead of guessing or using `any`

### Implementation Flow
1. **Pattern Discovery**: Search for similar implementations (use Grep/Glob)
2. **Context Assembly**: Read all relevant files upfront
3. **Analysis Before Action**: Investigate thoroughly before implementing
4. **Direct Work** for 1-4 file changes or active debugging
5. **Deploy Agents** for complex features, parallel work, or large investigations

### Code Standards
- Line length: 100 characters (Ruff enforced)
- Naming: `snake_case` modules, `PascalCase` classes, `UPPER_SNAKE_CASE` constants
- Adapters named for their system: `neo4j_writer.py`, `qdrant_client.py`
- All functions have type hints
- No comments unless explicitly requested (code should be self-documenting)
- No emoji in code (breaks across environments)

## Performance Targets (RTX 4070 GPU)

**Extraction Pipeline**:
- Tier A: ≥50 pages/sec (CPU)
- Tier B: ≥200 sentences/sec (md model) or ≥40 (trf model)
- Tier C: median ≤250ms/window, p95 ≤750ms (batched 8-16)

**Database Operations**:
- Neo4j: ≥20k edges/min with 2k-row UNWIND batches
- Qdrant: ≥5k vectors/sec (1024-dim HNSW indexing)

## Observability Requirements

### Logging
- JSON structured logs in all production code
- Chain traceability: `doc_id → section → windows → triples → Neo4j txId`
- Include: timestamp, level, service, operation, duration, error details

### Metrics (Aspirational)
- Windows/sec processed per tier
- Tier hit ratios (A vs B vs C usage)
- LLM latency p50/p95/p99
- Cache hit rates
- Database throughput

## Governance

### Authority
This constitution supersedes all other development practices. When in conflict, constitution rules take precedence.

### Amendment Process
1. Document the proposed change with rationale
2. Update constitution version (MAJOR for principle changes, MINOR for additions)
3. Update CHANGELOG.md with amendment details
4. No approval process needed (single-user system)

### Compliance
- All code must verify compliance with layering rules (core → adapters → apps)
- Complexity must be justified (default to simplicity)
- Violations should be fixed immediately (breaking changes are OK)

### Reference Documents
- **Architecture**: [CLAUDE.md](CLAUDE.md) - Development guidance for AI assistants
- **Setup**: [README.md](README.md) - Getting started and deployment
- **Changes**: [CHANGELOG.md](CHANGELOG.md) - Version history
- **API**: [apps/api/docs/](apps/api/docs/) - Service interfaces

**Version**: 1.0.0 | **Ratified**: 2025-10-20 | **Last Amended**: 2025-10-20
