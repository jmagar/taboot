# Extraction Package Audit Report

**Audit Date:** 2025-10-23
**Scope:** packages/extraction/ — Complete tiered extraction pipeline
**Target:** Verify Tier A, B, C implementations against EXTRACTION_SPEC.md

---

## Executive Summary

The extraction package has **foundational implementations** for Tier A and B, with a **skeleton for Tier C**. Core documentation is comprehensive and detailed. However, there are **significant gaps** between specification and implementation.

### Status Matrix

| Component | Specified | Implemented | Status |
|-----------|-----------|------------|--------|
| **Tier A (Deterministic)** | ✓ Complete | Partial | 🟡 50% |
| **Tier B (spaCy)** | ✓ Complete | Partial | 🟡 40% |
| **Tier C (LLM Windows)** | ✓ Complete | Skeleton | 🔴 20% |
| **Performance Instrumentation** | ✓ Yes | None | 🔴 0% |
| **Caching/DLQ** | ✓ Complete | None | 🔴 0% |
| **Tests** | Specified | Minimal | 🔴 0% |

---

## Documents Analyzed

1. **`packages/extraction/docs/EXTRACTION_SPEC.md`** (2.0.0, 2025-01-20)
   - 662 lines, comprehensive entity/relationship types
   - Performance targets clearly defined
   - Full schemas and examples provided

2. **`packages/extraction/docs/SPACY_TIER_B_RESEARCH.md`** (2025-10-20)
   - 1,217 lines of detailed research on spaCy implementation
   - Covers EntityRuler, DependencyMatcher, sentence classification
   - Code templates and benchmarks included

3. **`packages/extraction/README.md`**
   - Layout and guidelines for tier-based architecture
   - Key documentation references

4. **`packages/extraction/CLAUDE.md`**
   - Development guidance aligned with project conventions
   - Testing and quality standards

5. **`packages/extraction/tier_b/QUICK_START.md`** (2025-10-20)
   - Minimal working example (5 lines)
   - Production setup (3 steps)
   - Performance testing template

6. **`packages/extraction/tier_b/SPACY_PATTERNS_GUIDE.md`** (2025-10-20)
   - 1,915 lines of implementation patterns
   - Sections on EntityRuler, DependencyMatcher, classification, caching
   - Complete TierBExtractor class template

7. **`packages/extraction/tier_b/RESEARCH_SUMMARY.md`** (2025-10-20)
   - Executive summary of Tier B research
   - Key findings and recommendations
   - Integration checklist

---

## Tier A (Deterministic) Implementation

### Specification Requirements (EXTRACTION_SPEC.md § 4)

**Objective:** Fast, low-cost parsing of structured patterns.

**Target Performance:** ≥50 pages/sec (CPU)

**Required Techniques:**
- Regex + YAML/JSON parsers
- Aho-Corasick dictionary matching (known services)
- Link graph and fenced code parsing
- IP/hostname/port pattern matching

**Service Dictionary:** nginx, traefik, postgres, mysql, redis, mongodb, elasticsearch, neo4j, qdrant, etc.

### Implementation Files

#### 1. `/home/jmagar/code/taboot/packages/extraction/tier_a/patterns.py` (82 lines)

**Status:** ✓ Partially Implemented

```python
class EntityPatternMatcher:
    """Aho-Corasick-based pattern matcher for known entities."""
    - add_patterns(entity_type, patterns)  # ✓ Works
    - find_matches(text)                   # ✓ Works
```

**Issues:**
- Uses simple regex, NOT true Aho-Corasick automaton
- No actual pyahocorasick library import
- Regex is built per type, not optimized Aho-Corasick structure
- Comment claims Aho-Corasick but implementation uses re.compile()

**Grade:** 🟡 6/10 — Basic pattern matching works, but misses performance optimization

#### 2. `/home/jmagar/code/taboot/packages/extraction/tier_a/parsers.py` (101 lines)

**Status:** ✓ Mostly Implemented

```python
Functions:
- parse_code_blocks(content)        # ✓ Regex fenced code blocks
- parse_tables(content)             # ✓ Markdown table parsing
- parse_yaml_json(content, format)  # ✓ YAML/JSON parsing
```

**Strengths:**
- Handles all three required formats
- Simple, deterministic
- Proper error handling (returns None on parse failure)

**Gaps:**
- No Docker Compose parsing (mentioned in EXTRACTION_SPEC.md)
- No SWAG proxy config parsing
- No Tailscale/UniFi API config parsing
- No link graph extraction

**Grade:** 🟡 5/10 — Covers basic cases, missing domain-specific structured data

### Tier A Performance Status

**Target:** ≥50 pages/sec

**Current:** Unknown (no instrumentation)

**Issues:**
- No timing/metrics collection
- No batch processing implementation
- No Redis caching for parsed results

---

## Tier B (spaCy) Implementation

### Specification Requirements (EXTRACTION_SPEC.md § 4)

**Objective:** Capture grammatical relations and entity co-occurrences.

**Target Performance:** ≥200 sentences/sec (en_core_web_md) or ≥40 sentences/sec (trf)

**Base Model:** en_core_web_md (preferred) or en_core_web_trf

**Required Components:**
1. EntityRuler (Services, IPs, Ports, Hostnames, Endpoints)
2. DependencyMatcher (DEPENDS_ON, ROUTES_TO, BINDS, EXPOSES_ENDPOINT)
3. SentenceClassifier (technical vs. noise filtering)
4. Batch processing (nlp.pipe() with batch_size=1000)
5. Caching (Redis with content hashing)

### Implementation Files

#### 1. `/home/jmagar/code/taboot/packages/extraction/tier_b/entity_ruler.py` (92 lines)

**Status:** ⚠️ Partial Stub

```python
class SpacyEntityRuler:
    """Pattern-based entity extractor for technical entities."""
    - __init__(model)                 # Dummy parameter
    - _build_patterns()               # ✓ Basic regex patterns
    - extract_entities(text)          # ✓ Works with regex
```

**Critical Issues:**
- **Does not use spaCy at all** — Implements regex fallback instead
- Comment: "Uses regex patterns instead of spaCy models for deployment simplicity"
- Does not use actual spacy.pipeline.EntityRuler
- No DependencyMatcher, no sentence classification

**Patterns Defined:**
```python
SERVICE: nginx, postgres, redis, etc.  ✓
IP: Simple 4-octet pattern             ⚠️ Too broad (no validation)
PORT: \d{2,5}                          ⚠️ Matches invalid ports 00-99
HOST: server\d+, host\d+               ⚠️ Very limited
```

**Grade:** 🔴 2/10 — Not spaCy-based; pure regex with weak patterns

#### 2. `/home/jmagar/code/taboot/packages/extraction/tier_b/dependency_matcher.py` (69 lines)

**Status:** 🔴 Not Implemented

```python
class DependencyMatcher:
    """Extract relationships between entities using dependency patterns."""
    - __init__()                      # Empty
    - _build_patterns()               # Regex patterns, not dependency parsing
    - extract_relationships(text)     # Regex-based, not NLP-based
```

**Critical Issues:**
- **Does not use spaCy DependencyMatcher**
- Uses regex, not dependency parse trees
- Pattern examples:
  ```python
  DEPENDS_ON: r"(\w+)\s+(?:depends?\s+on|requires?|needs?)\s+(\w+)"
  ROUTES_TO: r"(\w+)\s+(?:routes?|forwards?)\s+(?:to\s+)?(\w+)"
  ```
- No grammatical understanding (e.g., won't handle "depends" vs "dependent")

**Grade:** 🔴 1/10 — Completely missed spaCy integration

#### 3. `/home/jmagar/code/taboot/packages/extraction/tier_b/window_selector.py` (131 lines)

**Status:** ✓ Basic Implementation

```python
class WindowSelector:
    """Select micro-windows (≤512 tokens) for Tier C LLM extraction."""
    - __init__(max_tokens=512)        # ✓
    - _estimate_tokens(text)          # ✓ Rough: 1.3 tokens/word
    - _split_into_sentences(text)     # ✓ Simple regex split
    - select_windows(text)            # ✓ Returns window dicts
```

**Strengths:**
- Respects 512-token limit per EXTRACTION_SPEC.md
- Returns structured windows with positions
- Handles sentence overflow

**Gaps:**
- No spaCy sentence segmentation (uses regex)
- No entity density scoring
- No technical sentence filtering
- No dependency keyword detection
- Token estimation is crude (1.3 multiplier)

**Grade:** 🟡 6/10 — Works but missing Tier B filtering logic

### Tier B Performance Status

**Target:** ≥200 sentences/sec

**Current:** Unknown (no instrumentation)

**Issue:** All three components are NOT integrated with spaCy as specified.

**What's Missing:**
- [ ] Load `en_core_web_md` model
- [ ] Add EntityRuler before NER
- [ ] Initialize DependencyMatcher from parser
- [ ] Custom sentence classifier component
- [ ] Batch processing with nlp.pipe()
- [ ] Reproducibility (seed fixing)
- [ ] Performance monitoring

---

## Tier C (LLM Windows) Implementation

### Specification Requirements (EXTRACTION_SPEC.md § 4)

**Objective:** Resolve ambiguous spans and extract nuanced relationships.

**Runtime:** Qwen3-4B-Instruct via Ollama (GPU-quantized)

**Window Policy:**
- Input window ≤512 tokens
- Batching: 8–16 windows per request
- Cache: SHA-256(window + version) in Redis (TTL: 7 days)

**Output Schema:**
```json
{
  "entities": [...],
  "relations": [...],
  "provenance": {"docId": "...", "section": "...", "span": [...]}
}
```

**Target Performance:** Median ≤250ms/window, P95 ≤750ms

### Implementation Files

#### 1. `/home/jmagar/code/taboot/packages/extraction/tier_c/schema.py` (19 lines)

**Status:** ✓ Basic Schema

```python
class Triple(BaseModel):
    subject: str
    predicate: str
    object: str
    confidence: float

class ExtractionResult(BaseModel):
    triples: list[Triple]
```

**Issues:**
- Missing entity types from EXTRACTION_SPEC.md
- No "entity type" field (Service, Host, IP, etc.)
- No relationship properties (host, path, port for ROUTES_TO)
- No provenance fields (docId, section, span)
- Doesn't match output schema in spec

**Grade:** 🟡 3/10 — Minimal schema, misses spec requirements

#### 2. `/home/jmagar/code/taboot/packages/extraction/tier_c/llm_client.py` (178 lines)

**Status:** 🟡 Partial Skeleton

```python
class TierCLLMClient:
    """Ollama LLM client with batching and Redis caching."""
    - __init__(model, redis_client, batch_size, temperature) # ✓
    - _compute_cache_key(window)      # ✓ SHA-256
    - _check_cache(cache_key)         # Stub (async, no implementation details)
    - _save_to_cache(...)             # Stub
    - _call_ollama(window)            # Stub with hardcoded prompt
    - extract_from_window(window)     # ✓ Cache check + LLM call
    - batch_extract(windows)          # Partial loop, no concurrent batching
```

**Strengths:**
- Redis caching structure present
- SHA-256 hashing for cache keys ✓
- Batch loop implemented

**Critical Issues:**
- **Ollama client code is untested/incomplete**
  ```python
  if AsyncClient is not None:
      self.ollama_client = AsyncClient()  # No host/port config
  ```
- **Hardcoded prompt missing examples**
  ```python
  prompt = f"""Extract knowledge triples from the following text.
  Return ONLY a JSON object..."""
  ```
  - No few-shot examples per EXTRACTION_SPEC.md (3-5 examples)
  - No confidence scoring logic
  - Prompt doesn't mention entity types

- **Batching is sequential, not concurrent**
  ```python
  for window in batch:
      result = await self.extract_from_window(window)  # Sequential!
  ```

- **No error handling for malformed JSON**
  - Silently returns empty result

- **No confidence filtering**
  - Spec says: "Filter extraction if confidence < 0.70; re-extract if 0.70-0.80"

- **No token-level logprobs**
  - Spec recommends logprobs for confidence scoring

**Grade:** 🔴 4/10 — Framework present, implementation incomplete

---

## Performance Instrumentation

### Specification Requirements (EXTRACTION_SPEC.md § 11)

**Metrics to Track:**
- Throughput: Pages/sec (A), Sentences/sec (B), Windows/sec (C)
- Latency: p50, p95, p99 per tier
- Quality: Tier hit ratios, confidence scores, F1 per type
- Cache: Redis hit rate, eviction rate, DLQ size
- Graph: Edges written/min, batch write latency

**Tracing Chain:**
```
docId → section → windows → triples → Neo4j txId
```

### Current Implementation

**Status:** 🔴 None

**What's Missing:**
- [ ] Metrics collection (no counters, timers)
- [ ] Performance logging
- [ ] Cache hit rate tracking
- [ ] Latency histograms (p50, p95, p99)
- [ ] Confidence score distribution
- [ ] DLQ size monitoring
- [ ] Neo4j write throughput metrics
- [ ] Integration with `packages.common` observability

---

## Caching and Dead Letter Queue (DLQ)

### Specification Requirements (EXTRACTION_SPEC.md §§ 5, 10)

**Cache Strategy:**
- Redis key patterns: `extraction:{content_hash}`, `extraction:meta:{content_hash}`
- TTL: 7 days
- SHA-256 content hashing
- Version-based invalidation

**DLQ:**
```
dlq:extraction:{content_hash} → Failed extraction
dlq:retry:{content_hash} → Retry count
dlq:failed:{content_hash} → Permanently failed
```
- Max 3 retries
- Exponential backoff: 1s, 5s, 25s
- 30-day retention

### Current Implementation

**Status:** 🔴 None in Tier A/B, Skeleton in Tier C

**Tier C (llm_client.py):**
- `_check_cache()` / `_save_to_cache()` are stubs
- Redis client passed but not configured
- No retry logic
- No DLQ management

**Missing in Tier A/B:**
- No caching at all
- No DLQ for failed parsing
- No retry mechanism

---

## Testing

### Specification Requirements

**Target:** ≥85% coverage in `packages/core` and extraction logic

**Test Markers:** `unit`, `integration`, `slow`, source-specific

### Current Implementation

**Status:** 🔴 No tests found

```bash
$ find /home/jmagar/code/taboot/tests/extraction -name "*.py" 2>/dev/null
[No output]
```

**Missing:**
- [ ] Unit tests for Tier A parsers
- [ ] Unit tests for Tier B entity/relationship extraction
- [ ] Unit tests for Tier C LLM client
- [ ] Integration tests (Tier A → B → C flow)
- [ ] Performance benchmarks
- [ ] Reproducibility tests
- [ ] Cache/DLQ tests

---

## Orchestrator Integration

### Implementation: `/home/jmagar/code/taboot/packages/extraction/orchestrator.py` (269 lines)

**Status:** ✓ Structure Present, Incomplete Wiring

```python
class ExtractionOrchestrator:
    async def process_document(doc_id, content):
        1. Create ExtractionJob (PENDING)
        2. Run Tier A → TIER_A_DONE
        3. Run Tier B → TIER_B_DONE
        4. Run Tier C → TIER_C_DONE
        5. Finalize → COMPLETED
```

**Strengths:**
- State machine design ✓
- Redis integration ✓
- Retry logic (3 retries) ✓

**Issues:**
- `_run_tier_a()` returns int (triple count) — doesn't return actual triples
- `_run_tier_b()` returns window count — doesn't pass to Tier C properly
- `_run_tier_c()` receives windows but orchestrator doesn't connect Tier B output correctly
- No validation of tier outputs
- No error details stored (empty dict)

**Grade:** 🟡 6/10 — Good structure, incomplete execution

---

## Entity Types Coverage

### Specification Requirements (EXTRACTION_SPEC.md §§ 2)

**Core Infrastructure Entities (11):**
Host, Container, Service, Endpoint, Network, IP, User, Credential, Repository, Package, Document

**Extended Infrastructure (15):**
ReverseProxy, VirtualHost, Route, Upstream, Backend, Image, ImageLayer, Volume, Interface, VLAN, Switch, Router, Gateway, AccessPoint, VPNTunnel

**Domain-Specific (5):**
TailscaleNode, Tailnet, UnifiSite, UnifiDevice, UnifiClient, DNSZone, DNSRecord, ConsulService

### Current Implementation

**Implemented:**
- SERVICE (basic regex)
- IP (basic regex)
- PORT (basic regex)
- HOST (basic regex)
- ENDPOINT (window selector only)

**Missing:**
- Container, Network, User, Credential, Repository, Package, Document
- ReverseProxy, VirtualHost, Route, Upstream, Backend
- Image, ImageLayer, Volume, Interface, VLAN
- Switch, Router, Gateway, AccessPoint, VPNTunnel
- TailscaleNode, Tailnet, UnifiSite, UnifiDevice, UnifiClient
- DNSZone, DNSRecord, ConsulService

**Coverage:** 5/34 = **14.7%**

---

## Relationship Types Coverage

### Specification Requirements (EXTRACTION_SPEC.md § 3)

**Implemented (Tier B):**
- DEPENDS_ON (regex pattern)
- ROUTES_TO (regex pattern)
- CONNECTS_TO (regex pattern)

**Not Implemented:**
- BINDS_TO, RESOLVES_TO, CONTAINS
- EXPOSES, USES_CREDENTIAL, BUILDS, MENTIONS, RUNS_IN
- CONNECTS_TO (full), MOUNTS_VOLUME, EXTENDS, BASED_ON
- CONSISTS_OF, CONTAINS_PACKAGE, HAS_INTERFACE, ASSIGNED_TO
- BELONGS_TO_VLAN, TRUNK_LINK, ADJACENT_TO
- HAS_VIRTUAL_HOST, HAS_ROUTE, USES_UPSTREAM, DISTRIBUTES_TO
- PEERS_WITH, MEMBER_OF
- DERIVED_FROM, ATTRIBUTED_TO, GENERATED_BY

**Coverage:** 3/31 = **9.7%**

---

## Documentation vs. Implementation Gap

### Specification Completeness

| Section | Completeness | Implementation % |
|---------|--------------|-----------------|
| 1. Purpose | 100% detailed | 30% |
| 2. Entity Types | 34 types defined | 15% (5/34) |
| 3. Relationship Types | 31 types defined | 10% (3/31) |
| 4. Extraction Tiers | Very detailed | 40% |
| 5. Entity Resolution | Comprehensive | 0% |
| 6. Graph Constraints | Cypher provided | 0% |
| 7. Batch Writing | UNWIND patterns | 0% |
| 8. Validation | Metrics defined | 0% |
| 9. Optimizations | Complete | 5% |
| 10. DLQ | Full strategy | 5% (Tier C only) |
| 11. Observability | Detailed | 0% |

---

## Summary Table

### Features Documented vs. Implemented

| Feature | Spec | Impl | Status | Grade |
|---------|------|------|--------|-------|
| **Tier A Patterns** | ✓ | 🟡 Regex not Aho-Corasick | 6/10 |
| **Tier A Parsing** | ✓ | 🟡 Basic only | 5/10 |
| **Tier B EntityRuler** | ✓ | ❌ Regex not spaCy | 2/10 |
| **Tier B DependencyMatcher** | ✓ | ❌ Regex not NLP | 1/10 |
| **Tier B Sentence Classifier** | ✓ | ❌ Not implemented | 0/10 |
| **Tier B Batch Processing** | ✓ | ❌ Not implemented | 0/10 |
| **Tier B Caching** | ✓ | ❌ Not implemented | 0/10 |
| **Tier C LLM** | ✓ | 🟡 Skeleton | 4/10 |
| **Tier C Caching** | ✓ | 🟡 Stub | 2/10 |
| **Entity Types** | 34 | 5 | 15% |
| **Relationship Types** | 31 | 3 | 10% |
| **Performance Metrics** | ✓ | ❌ None | 0/10 |
| **DLQ/Retry** | ✓ | 🟡 Skeleton | 5% |
| **Tests** | ✓ | ❌ None | 0/10 |
| **Orchestration** | ✓ | 🟡 Incomplete | 6/10 |

---

## Critical Gaps

### Tier A
1. **Aho-Corasick not implemented** — Uses regex instead (performance issue)
2. **Docker Compose parsing missing** — Critical for homelab extraction
3. **SWAG/proxy config parsing missing**
4. **No Tailscale/UniFi API parsing**
5. **No caching/DLQ**
6. **No performance instrumentation**

### Tier B
1. **Does not use spaCy** — All three components (EntityRuler, DependencyMatcher, Classifier) use regex instead
2. **No model loading** — en_core_web_md not integrated
3. **No sentence classification** — Not distinguishing technical vs. noise
4. **No batch processing** — nlp.pipe() not used
5. **No caching**
6. **No reproducibility setup** (seeds, PYTHONHASHSEED)
7. **No performance metrics**

### Tier C
1. **Prompts lack few-shot examples** — Spec requires 3-5 examples per entity type
2. **No confidence filtering** — Spec requires <0.70 filtering
3. **No token-level logprobs** — Recommended for confidence scoring
4. **Batching is sequential, not concurrent**
5. **Incomplete Ollama config** — No host/port specification
6. **Schema doesn't match spec** — Missing entity types, relationship properties, provenance

### Cross-Cutting
1. **No tests** — Zero coverage
2. **No observability** — No metrics, logging, or tracing
3. **No entity resolution** — Graph merging strategy not implemented
4. **No Neo4j constraints** — Graph model not initialized
5. **No DLQ in A/B** — Only skeleton in C
6. **Low entity/relationship coverage** — 15% and 10% respectively

---

## Recommendations

### Priority 1 (Blocking)
1. **Replace regex with spaCy in Tier B**
   - Load en_core_web_md
   - Implement proper EntityRuler
   - Implement DependencyMatcher
   - Add sentence classifier

2. **Add Tier B caching**
   - Redis integration with content hashing
   - Version-based invalidation

3. **Complete Tier C prompting**
   - Add 3-5 few-shot examples per entity type
   - Implement confidence filtering
   - Add token logprob extraction

### Priority 2 (Important)
1. **Implement Docker Compose parsing in Tier A**
2. **Add performance instrumentation** (metrics, logging)
3. **Add comprehensive test suite** (unit + integration)
4. **Implement entity resolution** (Neo4j merging logic)
5. **Add DLQ to Tier A** (for failed parsing)

### Priority 3 (Enhancement)
1. **Aho-Corasick optimization in Tier A** (if performance becomes bottleneck)
2. **SWAG/proxy config parsing**
3. **Tailscale/UniFi API parsing**
4. **GPU acceleration for Tier B** (en_core_web_trf if needed)
5. **Distributed caching** (Redis cluster)

---

## Implementation Checklist

### Immediate (Week 1)
- [ ] Create test file: `tests/extraction/test_tier_a.py`
- [ ] Create test file: `tests/extraction/test_tier_b.py`
- [ ] Create test file: `tests/extraction/test_tier_c.py`
- [ ] Rewrite Tier B to use actual spaCy (not regex)
- [ ] Add Redis caching to Tier B
- [ ] Complete Tier C prompting with examples

### Short-term (Week 2-3)
- [ ] Add Docker Compose parser to Tier A
- [ ] Implement performance metrics (counters, timers)
- [ ] Add DLQ/retry to Tier A
- [ ] Fix Tier C schema to match spec
- [ ] Implement entity resolution in orchestrator

### Medium-term (Week 4+)
- [ ] Add SWAG proxy parsing
- [ ] Implement Neo4j constraints in initialization
- [ ] Add Tailscale/UniFi parsers
- [ ] Reach 85% test coverage
- [ ] Optimize Aho-Corasick if needed

---

## Conclusion

The extraction package has **solid documentation but weak implementation**. The specifications are detailed and well-researched, but the code takes shortcuts (regex instead of spaCy, no caching, no tests). This creates a **high spec-implementation mismatch (40-50% implementation vs 100% spec)**.

The foundation is present (orchestrator, basic parsing, window selection), but **Tier B needs a complete rewrite** to use spaCy as specified, and **Tier C needs critical enhancements** to production standards.

**Estimated effort to production-ready:**
- Tier A: 1-2 weeks (parsing + caching)
- Tier B: 2-3 weeks (spaCy rewrite + caching + tests)
- Tier C: 1-2 weeks (prompting + schemas + tests)
- Cross-cutting: 1-2 weeks (metrics, entity resolution, tests)

**Total: 5-9 weeks to reach 80%+ implementation.**
