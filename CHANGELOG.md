# Changelog

All notable changes to Taboot will be documented in this file.

**Note**: This is a single-user system with no backwards compatibility guarantees. Breaking changes are acceptable and expected. When in doubt, wipe and rebuild databases.

## [Unreleased]

### Changed
- Renamed project from LlamaCrawl to Taboot across all documentation and code
- Standardized all health check endpoints to `/health` (previously mixed `/health` and `/healthz`)
- Updated all environment variable references (LLAMACRAWL_* → TABOOT_*)
- Removed legacy `uv run taboot-api` entry point (API runs via Docker only)
- Docker service name changed from `taboot-api` to `taboot-app` in documentation
- Updated CLI command name from `llama` to `taboot`
- Removed abstract port pattern in favor of direct imports from adapter packages
- Added prominent single-user system philosophy notes to README.md and CLAUDE.md

### Fixed
- Fixed FIRECRAWL_PORT and FIRECRAWL_INTERNAL_PORT variable naming in .env files
- Fixed NUQ_DATABASE_URL to use ${POSTGRES_DB} variable instead of hardcoded 'postgres'
- Added TABOOT_HTTP_PORT environment variable
- Added port mapping comments (host→container) for all services in .env files
- Fixed Ollama model name in troubleshooting guide

### Added
- Port mapping documentation in .env.example with inline comments
- Direct import pattern example in packages/core/README.md
- CHANGELOG.md for tracking project changes
- Project constitution (.specify/memory/constitution.md) defining core principles, tech stack, and development workflow
- Comprehensive testing documentation (docs/TESTING.md) covering unit/integration tests, markers, patterns, and troubleshooting
- LlamaIndex usage clarified across all adapter packages (ingest, extraction, vector, graph, retrieval)

## [0.4.0] - 2025-10-20

Initial taboot release with complete documentation audit and naming update.
