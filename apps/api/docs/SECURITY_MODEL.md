# Security Model

Threats and controls for crawling untrusted content and storing derived knowledge.

## Authentication & Authorization

* **API:** API key via `X-API-Key`. Rotate keys; store hashed in Postgres.
* **Service-to-service:** optional mTLS between API and internal services.
* **Scopes:** simple per-namespace scope on keys (read|write|admin).

## Network Boundaries

* Private network for Qdrant, Neo4j, Redis, Postgres. API is the only public entry.
* Egress firewall/allowlist for crawler; prevent SSRF to internal ranges.

## Playwright/Browser Hardening

* Disable file downloads, camera/mic.
* Block `file://`, `ftp://`, and private IP ranges.
* Limit navigation to allowed schemes.
* Cap resource sizes; abort giant downloads.

## Input Sanitization

* Treat all HTML as hostile. Sanitize before rendering anywhere.
* Strip scripts when storing previews; keep raw for text extraction only.

## SSRF & URL Validation

* Validate URLs against allow/deny lists before scheduling.
* Resolve DNS before fetch; drop IP literals pointing to RFC1918 ranges.

## Secrets Handling

* `.env` for local only; mount sealed secrets in prod.
* Rotate credentials quarterly; record `rotates_after` on `Credential` nodes for reminders.

## Data Minimization

* Store only necessary payload in Qdrant; keep PII out unless required.
* Hash or redact tokens in logs.

## Dependency & Supply Chain

* Pin versions in `requirements.txt`/lockfiles.
* Verify container images; prefer distroless where possible.
* Scan images weekly.

## Threat Model (high-level)

* **T1:** SSRF via crafted links → mitigate with egress filter, URL validation, DNS allowlist.
* **T2:** Browser sandbox escape → run as non-root, seccomp, up-to-date Playwright.
* **T3:** Data poisoning in RAG → provenance tracking, domain trust levels, and reranker sanity checks.
* **T4:** Credential leakage in logs → structured logging with filters and unit tests for redaction.

## Incident Response

* Rotate API keys.
* Purge compromised namespace from Qdrant and Neo4j; see DATA_GOVERNANCE.md.
* Snapshot before purge when possible.
