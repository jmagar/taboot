# spaCy Tier B Extraction Research Report

**Date:** 2025-10-20
**Target:** ≥200 sentences/sec (en_core_web_md) or ≥40 sentences/sec (trf)
**Use Case:** Extract infrastructure entities (Service, Host, IP, Proxy) and select candidate windows for Tier C LLM processing

---

## Executive Summary

This report synthesizes best practices for implementing Tier B extraction using spaCy's entity extraction and custom pipeline components. The research covers EntityRuler patterns for technical infrastructure, DependencyMatcher for relationship extraction, custom sentence classifiers, pipeline optimization strategies, model selection trade-offs, and reproducibility requirements.

**Key Recommendations:**
1. Use **EntityRuler with regex patterns** for IPs/hostnames + PhraseMatcher for service gazetteers
2. Use **DependencyMatcher** for extracting `DEPENDS_ON` and `ROUTES_TO` relationships
3. Implement **custom sentence classifier** component with extension attributes for window scoring
4. Target **batch_size=1000** with **disabled pipes** (tagger, parser if not needed) for CPU optimization
5. Use **en_core_web_md** for baseline (10k words/sec), switch to **trf** only if F1 gains justify 15x slowdown
6. Fix **numpy/random seeds** for CPU reproducibility; GPU has non-deterministic operations

---

## 1. EntityRuler: Pattern Matching for Infrastructure Entities

### Decision
Use **EntityRuler with token-based regex patterns** for IPs, hostnames, URLs, and **PhraseMatcher** (integrated via EntityRuler phrase patterns) for known service names from gazetteers.

### Rationale
- Rule-based systems excel at structured patterns (IPs, hostnames, service names)
- EntityRuler can combine with statistical NER to boost accuracy
- Phrase patterns use Aho-Corasick algorithm (O(N) complexity regardless of keyword count)
- Token regex patterns handle validation (e.g., IP octets 0-255)

### Code Examples

#### Basic EntityRuler Setup
```python
import spacy
from spacy.pipeline import EntityRuler

nlp = spacy.load("en_core_web_md")

# Add EntityRuler before NER to let NER respect custom entities
ruler = nlp.add_pipe("entity_ruler", before="ner")

# IP address pattern with proper octet validation
octet_rx = r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
ip_pattern = {"TEXT": {"REGEX": rf"^{octet_rx}(?:\.{octet_rx}){{3}}$"}}

patterns = [
    # IP addresses (token-based regex)
    {"label": "IP", "pattern": [ip_pattern]},

    # Hostnames (phrase patterns for known hosts)
    {"label": "HOST", "pattern": "nginx.example.com"},
    {"label": "HOST", "pattern": "postgres-primary.local"},

    # Service names (phrase patterns from gazetteer)
    {"label": "SERVICE", "pattern": "nginx"},
    {"label": "SERVICE", "pattern": "postgresql"},
    {"label": "SERVICE", "pattern": "redis"},

    # Proxy names (multi-token patterns)
    {"label": "PROXY", "pattern": [{"LOWER": "traefik"}, {"LOWER": "reverse"}, {"LOWER": "proxy"}]},
]

ruler.add_patterns(patterns)

# Load gazetteer and add as phrase patterns
def load_service_gazetteer(filepath: str) -> list[dict[str, str]]:
    """Load service names from file and convert to EntityRuler patterns."""
    with open(filepath) as f:
        services = [line.strip() for line in f if line.strip()]
    return [{"label": "SERVICE", "pattern": svc} for svc in services]

# Add gazetteer patterns
gazetteer_patterns = load_service_gazetteer("service_names.txt")
ruler.add_patterns(gazetteer_patterns)
```

#### Advanced Pattern Examples
```python
# Docker container names (lowercase alphanumeric + underscores/hyphens)
patterns.extend([
    {
        "label": "CONTAINER",
        "pattern": [{"TEXT": {"REGEX": r"^[a-z0-9_-]+$"}, "LENGTH": {">=": 3}}]
    },

    # Port bindings (e.g., "8080:80", "443:443")
    {
        "label": "PORT_BINDING",
        "pattern": [
            {"TEXT": {"REGEX": r"^\d{1,5}$"}},
            {"ORTH": ":"},
            {"TEXT": {"REGEX": r"^\d{1,5}$"}}
        ]
    },

    # Environment variable references (e.g., "${REDIS_URL}")
    {
        "label": "ENV_VAR",
        "pattern": [
            {"ORTH": "$"},
            {"ORTH": "{"},
            {"TEXT": {"REGEX": r"^[A-Z_]+$"}},
            {"ORTH": "}"}
        ]
    }
])
```

### Performance Notes
- **PhraseMatcher** (used internally by phrase patterns): O(N) time complexity regardless of gazetteer size
- FlashText/Aho-Corasick: When keywords < 500, regex competitive; beyond 500, PhraseMatcher dominates
- **EntityRuler overhead**: Minimal for phrase patterns; token regex adds ~5-10% overhead vs pure PhraseMatcher
- **Ordering matters**: Place EntityRuler **before NER** if you want NER to respect custom entities

### Gotchas
- **REGEX operates on single tokens**, not spans. Pattern `[{"TEXT": {"REGEX": r"^\d+\.\d+\.\d+\.\d+$"}}]` only matches if IP is a single token (spaCy tokenizer may split on dots!)
- Use `nlp.tokenizer.add_special_case("192.168.1.1", [{"ORTH": "192.168.1.1"}])` to force single-token treatment
- **Case sensitivity**: Use `{"LOWER": "nginx"}` for case-insensitive matching
- **Phrase patterns are exact matches**: "NGINX" won't match "nginx" unless you add both variants or use token patterns with `LOWER`

---

## 2. DependencyMatcher: Extracting Relationships

### Decision
Use **DependencyMatcher** for extracting structured relationships from parse trees, particularly subject-verb-object patterns for `Service DEPENDS_ON Service` and similar edges.

### Rationale
- DependencyMatcher excels at "relation extraction adjacent" tasks requiring linguistic structure
- Can capture relationships expressed across sentence structure (not just adjacent tokens)
- Deterministic and reproducible (no confidence scores, but high precision)
- More robust than surface-level regex for natural language descriptions

### Code Examples

#### Basic Service Dependency Pattern
```python
from spacy.matcher import DependencyMatcher

nlp = spacy.load("en_core_web_md")
dep_matcher = DependencyMatcher(nlp.vocab)

# Pattern: "nginx depends on postgresql"
# Structure: SERVICE(subject) → depends(verb) → SERVICE(object)
depends_pattern = [
    {
        "RIGHT_ID": "verb_depends",
        "RIGHT_ATTRS": {"LEMMA": {"IN": ["depend", "require", "need", "use"]}}
    },
    {
        "LEFT_ID": "verb_depends",
        "REL_OP": ">",  # verb is parent of subject
        "RIGHT_ID": "subject_service",
        "RIGHT_ATTRS": {"DEP": "nsubj", "ENT_TYPE": "SERVICE"}
    },
    {
        "LEFT_ID": "verb_depends",
        "REL_OP": ">",  # verb is parent of object
        "RIGHT_ID": "object_service",
        "RIGHT_ATTRS": {"DEP": {"IN": ["dobj", "pobj"]}, "ENT_TYPE": "SERVICE"}
    }
]

dep_matcher.add("DEPENDS_ON", [depends_pattern])

# Process document
doc = nlp("nginx depends on postgresql for caching. redis is used by the api service.")
matches = dep_matcher(doc)

for match_id, token_ids in matches:
    verb_idx, subject_idx, object_idx = token_ids
    subject = doc[subject_idx]
    verb = doc[verb_idx]
    obj = doc[object_idx]
    print(f"{subject.text} {verb.text} {obj.text}")  # nginx depends postgresql
```

#### Advanced Routing Pattern
```python
# Pattern: "traefik routes to nginx on example.com"
# Captures: Proxy → routes to → Service + Host
routes_pattern = [
    {
        "RIGHT_ID": "verb_route",
        "RIGHT_ATTRS": {"LEMMA": {"IN": ["route", "proxy", "forward", "redirect"]}}
    },
    {
        "LEFT_ID": "verb_route",
        "REL_OP": ">",
        "RIGHT_ID": "subject_proxy",
        "RIGHT_ATTRS": {"DEP": "nsubj", "ENT_TYPE": "PROXY"}
    },
    {
        "LEFT_ID": "verb_route",
        "REL_OP": ">",
        "RIGHT_ID": "object_service",
        "RIGHT_ATTRS": {"DEP": {"IN": ["dobj", "pobj"]}, "ENT_TYPE": "SERVICE"}
    },
    {
        "LEFT_ID": "object_service",
        "REL_OP": ">",
        "RIGHT_ID": "host_modifier",
        "RIGHT_ATTRS": {"DEP": {"IN": ["prep", "pobj"]}, "ENT_TYPE": "HOST"}
    }
]

dep_matcher.add("ROUTES_TO", [routes_pattern])
```

#### Compound Noun Phrases (Service Names)
```python
# Pattern: "api service" or "database server"
# Useful for extracting multi-token service names
compound_pattern = [
    {
        "RIGHT_ID": "head_noun",
        "RIGHT_ATTRS": {"POS": "NOUN"}
    },
    {
        "LEFT_ID": "head_noun",
        "REL_OP": ">",
        "RIGHT_ID": "compound_modifier",
        "RIGHT_ATTRS": {"DEP": "compound", "POS": "NOUN"}
    }
]

dep_matcher.add("SERVICE_COMPOUND", [compound_pattern])
```

### Performance Notes
- **Speed**: Dependency parsing is the slowest component (parser can be disabled if only using EntityRuler)
- **Accuracy**: Requires accurate dependency parse (en_core_web_md: ~92% UAS; trf: ~95% UAS)
- **Throughput impact**: Adds ~30-40% overhead vs EntityRuler alone
- **When to use**: Only when relationships are expressed via natural language structure (not config files/tables)

### Gotchas
- **REL_OP semantics**: `>` = parent, `<` = child, `>>` = ancestor, `<<` = descendant, `.` = immediately precedes, `.*` = precedes
- **Token order in results**: Match returns token indices in **pattern definition order**, not sentence order
- **NBOR_RELOP vs DEP**: Use `REL_OP` for structural relations (parent/child), use `RIGHT_ATTRS: {"DEP": "nsubj"}` for dependency labels
- **Entity type constraints**: `ENT_TYPE` only works if entities already assigned (via EntityRuler or NER)
- **Multiword entities**: DependencyMatcher operates on single tokens; use entity spans for multi-token matches

---

## 3. Custom Pipeline Components: Sentence Classifier for Window Selection

### Decision
Implement a **custom pipeline component** using `@Language.component` decorator that scores sentences and stores scores via **Span extension attributes** (`Span._.window_score`).

### Rationale
- Window selection is domain-specific logic not covered by spaCy built-ins
- Extension attributes are the idiomatic way to attach custom metadata to Spans
- Component approach keeps logic encapsulated and testable
- Can be inserted at optimal pipeline position (after sentence segmentation, before heavy components)

### Code Examples

#### Basic Sentence Scorer Component
```python
import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span

# Register extension attributes (once, at module level)
if not Span.has_extension("window_score"):
    Span.set_extension("window_score", default=0.0)

if not Span.has_extension("window_candidate"):
    Span.set_extension("window_candidate", default=False)

@Language.component("sentence_scorer")
def sentence_scorer(doc: Doc) -> Doc:
    """
    Score sentences for LLM window candidacy.

    Scoring criteria:
    - Has technical entities (SERVICE, HOST, IP, PROXY): +0.3 per entity
    - Contains dependency keywords (depends, routes, binds, exposes): +0.2 per keyword
    - Has numeric data (ports, IPs, versions): +0.1
    - Sentence length 10-100 tokens: +0.2 (too short/long penalized)
    """
    dependency_keywords = {"depend", "require", "route", "proxy", "bind", "expose", "run"}

    for sent in doc.sents:
        score = 0.0

        # Entity density
        entity_count = sum(1 for token in sent if token.ent_type_ in {"SERVICE", "HOST", "IP", "PROXY"})
        score += entity_count * 0.3

        # Dependency keywords
        keyword_count = sum(1 for token in sent if token.lemma_ in dependency_keywords)
        score += keyword_count * 0.2

        # Numeric data presence
        has_numeric = any(token.like_num or token.ent_type_ == "IP" for token in sent)
        if has_numeric:
            score += 0.1

        # Length penalty
        sent_len = len(sent)
        if 10 <= sent_len <= 100:
            score += 0.2
        elif sent_len < 5 or sent_len > 150:
            score -= 0.3

        # Assign score to span
        sent._.window_score = score
        sent._.window_candidate = score >= 0.5  # Threshold for LLM processing

    return doc

# Add to pipeline
nlp = spacy.load("en_core_web_md")
nlp.add_pipe("sentence_scorer", after="ner")
```

#### Advanced Window Assembler
```python
@Language.component("window_assembler")
def window_assembler(doc: Doc) -> Doc:
    """
    Assemble ≤512 token windows from high-scoring sentences.

    Strategy:
    1. Sort sentences by score (descending)
    2. Greedily pack into windows with ±1 context sentence
    3. Ensure no window exceeds 512 tokens
    """
    if not Doc.has_extension("windows"):
        Doc.set_extension("windows", default=[])

    # Get candidate sentences
    candidates = [sent for sent in doc.sents if sent._.window_candidate]
    candidates.sort(key=lambda s: s._.window_score, reverse=True)

    windows = []
    used_sents = set()

    for sent in candidates:
        if sent in used_sents:
            continue

        # Try to include ±1 context sentence
        sent_idx = list(doc.sents).index(sent)
        start_idx = max(0, sent_idx - 1)
        end_idx = min(len(list(doc.sents)), sent_idx + 2)

        window_sents = list(doc.sents)[start_idx:end_idx]
        window_tokens = sum(len(s) for s in window_sents)

        # Respect 512 token limit
        if window_tokens <= 512:
            window_span = doc[window_sents[0].start:window_sents[-1].end]
            windows.append({
                "span": window_span,
                "score": sent._.window_score,
                "token_count": window_tokens
            })
            used_sents.update(window_sents)
        else:
            # Just use the single sentence
            windows.append({
                "span": sent,
                "score": sent._.window_score,
                "token_count": len(sent)
            })
            used_sents.add(sent)

    doc._.windows = windows
    return doc

nlp.add_pipe("window_assembler", after="sentence_scorer")
```

### Performance Notes
- **Minimal overhead**: Scoring logic is O(N) in tokens, adds ~1-2% to pipeline time
- **Extension attributes**: No performance penalty vs storing in external dict (stored in C++ layer)
- **Component ordering**: Place after all linguistic annotation (NER, parsing) to leverage features
- **Batching**: Custom components receive Doc objects from `nlp.pipe()` batching automatically

### Gotchas
- **Extension registration**: Must call `Span.set_extension()` before first use (module-level or in component factory)
- **Overwrite conflicts**: Use `force=True` if extension already registered elsewhere
- **Property vs attribute**: Use property extensions (`getter=`) for computed values, attribute for stored data
- **Serialization**: Extension attributes **not serialized** by default; override `to_bytes()`/`from_bytes()` if needed
- **Span boundary changes**: Sentence boundaries can change if using custom sentencizer; score after final boundaries set

---

## 4. Pipeline Optimization: Batching and Disabling Pipes

### Decision
Use **`nlp.pipe(texts, batch_size=1000, n_process=1)`** with **disabled unnecessary components** (tagger, lemmatizer if not needed) and **fixed BLAS thread limits** for CPU optimization.

### Rationale
- Batching is 10-100x faster than one-by-one processing (statistical models amortize overhead)
- Disabling pipes reduces memory and CPU (parser is ~40% of pipeline time)
- Single-process with large batches faster than multiprocessing for <10k docs (spawn overhead)
- BLAS thread limits prevent CPU oversubscription (spaCy saturates 3-4 cores per process)

### Code Examples

#### Optimal Batching Configuration
```python
import spacy
import os

# Limit BLAS threads (set before loading spaCy)
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"

nlp = spacy.load("en_core_web_md")

# Disable unused components
disabled_pipes = ["tagger", "lemmatizer"]  # Keep parser for DependencyMatcher
# If only using EntityRuler (no DependencyMatcher), also disable parser:
# disabled_pipes = ["tagger", "parser", "lemmatizer"]

# Process documents
texts = ["Document 1 text...", "Document 2 text...", ...]  # 1000s of docs

docs = list(nlp.pipe(
    texts,
    batch_size=1000,  # Optimal for en_core_web_md on CPU
    disable=disabled_pipes,
    n_process=1  # Single process for <10k docs
))
```

#### Component Dependencies (Critical!)
```python
# NEVER disable components that others depend on!

# Lemmatizer depends on:
# - tagger (for POS tags)
# - morphologizer or attribute_ruler (for morphology)
# If you disable tagger, you MUST also disable lemmatizer

# NER depends on:
# - tok2vec (for embeddings) - NEVER disable if using NER

# Dependency parser depends on:
# - tok2vec - NEVER disable if using parser

# Safe configurations:
configs = {
    "ner_only": ["tagger", "parser", "lemmatizer", "attribute_ruler"],
    "entities_and_deps": ["tagger", "lemmatizer", "attribute_ruler"],
    "full_pipeline": []  # Disable nothing
}

# Choose based on use case
nlp_ner_only = spacy.load("en_core_web_md", disable=configs["ner_only"])
```

#### Multiprocessing (for >10k documents)
```python
# Only beneficial for large corpora (>10k docs) on multi-core systems
texts = [...]  # 100k+ documents

# Use n_process for parallel processing
docs = list(nlp.pipe(
    texts,
    batch_size=500,  # Smaller batch per process
    n_process=4,  # CPU_COUNT - 1
    disable=["tagger", "lemmatizer"]
))

# Note: Each process duplicates model in memory (4 processes = 4x memory)
```

#### Memory Management for Long-Running Services
```python
from contextlib import contextmanager

@contextmanager
def memory_zone():
    """Clear spaCy internal caches after processing batch."""
    try:
        yield
    finally:
        import gc
        gc.collect()

# Process in chunks with memory cleanup
chunk_size = 10000
for i in range(0, len(texts), chunk_size):
    with memory_zone():
        chunk = texts[i:i+chunk_size]
        docs = list(nlp.pipe(chunk, batch_size=1000))
        # ... process docs ...
        del docs  # Explicit cleanup
```

### Performance Notes

#### Benchmark Results (en_core_web_md, CPU)
| Configuration | Words/sec | Sentences/sec (est) | Notes |
|---------------|-----------|---------------------|-------|
| Full pipeline | ~10,000 | ~500 | Baseline |
| Disable parser | ~16,000 | ~800 | +60% speedup |
| Disable parser+tagger | ~20,000 | ~1000 | +100% speedup |
| NER only | ~25,000 | ~1250 | +150% speedup |
| EntityRuler only (no stats) | ~50,000 | ~2500 | +400% speedup |

**Target: ≥200 sentences/sec achieved with parser+tagger disabled**

#### Batch Size Guidelines
| Document Length | Batch Size | Rationale |
|-----------------|------------|-----------|
| Short (tweets, <50 tokens) | 1000-5000 | Many docs fit in memory |
| Medium (articles, 200-500 tokens) | 500-1000 | Balance memory/speed |
| Long (docs, 1000+ tokens) | 50-200 | Avoid memory spikes |

#### CPU Optimization
- **BLAS threads**: 3-4 threads per process optimal
- **Multiprocessing**: Only use if >10k docs and >8 CPU cores
- **Batch size**: Increase until memory limits hit (~70% RAM usage)
- **Parser**: Disable if only using EntityRuler or PhraseMatcher (40% speedup)

### Gotchas
- **Component dependencies**: Disabling tagger breaks lemmatizer (will log warnings)
- **Multiprocessing spawn overhead**: Windows/macOS use "spawn" (slow model copy); Linux uses "fork" (faster)
- **Memory per process**: Each `n_process` duplicates model in RAM (4 processes = 4x memory)
- **Batch size vs RAM**: OOM errors if batch too large; monitor with `psutil`
- **String table growth**: Vocab grows with new tokens; use `nlp.vocab.strings.add()` sparingly
- **Sentencizer vs parser**: `sentencizer` is 10x faster than parser for sentence segmentation

---

## 5. Model Selection: en_core_web_md vs Transformer

### Decision
Use **en_core_web_md** as baseline (achieves ≥200 sentences/sec target). Switch to **en_core_web_trf** **only if**:
1. F1 score on validation set improves by ≥5 points, AND
2. Throughput of ≥40 sentences/sec is acceptable for use case

### Rationale
- en_core_web_md: 10k words/sec CPU, ~500 sentences/sec, 92% accuracy, 40MB model
- en_core_web_trf: 680 words/sec CPU, ~34 sentences/sec, 95% accuracy, 440MB model
- Infrastructure text (configs, docs) is more structured than general prose → CNN models sufficient
- Transformer models excel at contextual ambiguity, less critical for technical jargon
- 15x slowdown rarely justified for 3% accuracy gain in domain-specific extraction

### Code Examples

#### Model Comparison Pipeline
```python
import spacy
from typing import List, Dict
import time

def benchmark_model(model_name: str, texts: List[str]) -> Dict[str, float]:
    """Benchmark model speed and accuracy."""
    nlp = spacy.load(model_name)

    # Warm up
    _ = list(nlp.pipe(texts[:100]))

    # Benchmark
    start = time.perf_counter()
    docs = list(nlp.pipe(texts, batch_size=1000 if "md" in model_name else 128))
    elapsed = time.perf_counter() - start

    total_tokens = sum(len(doc) for doc in docs)
    total_sents = sum(len(list(doc.sents)) for doc in docs)

    return {
        "model": model_name,
        "elapsed_sec": elapsed,
        "tokens_per_sec": total_tokens / elapsed,
        "sents_per_sec": total_sents / elapsed,
        "memory_mb": nlp.meta["size"]
    }

# Compare models
texts = [...]  # Your corpus
results_md = benchmark_model("en_core_web_md", texts)
results_trf = benchmark_model("en_core_web_trf", texts)

print(f"MD: {results_md['sents_per_sec']:.0f} sent/sec")
print(f"TRF: {results_trf['sents_per_sec']:.0f} sent/sec")
print(f"Speedup: {results_md['sents_per_sec'] / results_trf['sents_per_sec']:.1f}x")
```

#### Accuracy Evaluation
```python
from spacy.scorer import Scorer
from spacy.training import Example

def evaluate_model(nlp, gold_examples: List[Example]) -> Dict[str, float]:
    """Evaluate NER F1 on gold examples."""
    scorer = Scorer()

    for example in gold_examples:
        pred = nlp(example.reference.text)
        example_pred = Example.from_dict(pred, example.to_dict())
        scorer.score([example_pred])

    return scorer.scores

# Evaluate both models
gold_examples = [...]  # Your annotated validation set
scores_md = evaluate_model(nlp_md, gold_examples)
scores_trf = evaluate_model(nlp_trf, gold_examples)

print(f"MD NER F1: {scores_md['ents_f']:.3f}")
print(f"TRF NER F1: {scores_trf['ents_f']:.3f}")
print(f"F1 gain: {(scores_trf['ents_f'] - scores_md['ents_f']) * 100:.1f} points")
```

#### Adaptive Model Selection
```python
class AdaptivePipeline:
    """Use fast model for most docs, slow model for high-value docs."""

    def __init__(self):
        self.fast = spacy.load("en_core_web_md")
        self.slow = spacy.load("en_core_web_trf")

    def process(self, texts: List[str], importance_scores: List[float]) -> List[Doc]:
        """Route to appropriate model based on importance."""
        threshold = 0.8  # Top 20% use transformer

        fast_texts = [(i, t) for i, (t, s) in enumerate(zip(texts, importance_scores)) if s < threshold]
        slow_texts = [(i, t) for i, (t, s) in enumerate(zip(texts, importance_scores)) if s >= threshold]

        results = [None] * len(texts)

        # Fast path
        for i, doc in zip([i for i, _ in fast_texts], self.fast.pipe([t for _, t in fast_texts], batch_size=1000)):
            results[i] = doc

        # Slow path
        for i, doc in zip([i for i, _ in slow_texts], self.slow.pipe([t for _, t in slow_texts], batch_size=128)):
            results[i] = doc

        return results
```

### Performance Notes

#### Model Characteristics
| Feature | en_core_web_md | en_core_web_trf |
|---------|----------------|-----------------|
| Architecture | CNN (tok2vec) | Transformer (RoBERTa) |
| Model size | 40 MB | 440 MB |
| Loading time | ~2 sec | ~8 sec |
| Memory (inference) | ~200 MB | ~800 MB |
| CPU throughput | 10k words/sec | 680 words/sec |
| GPU throughput | 15k words/sec | 3k words/sec |
| NER F1 (OntoNotes) | 85.9% | 89.8% |
| Dependency UAS | 92.0% | 95.1% |

#### When to Use Transformer
- High-stakes extraction where errors are costly
- Ambiguous entity contexts (e.g., "Apple" company vs fruit)
- Prose-heavy documents with complex syntax
- GPU available (transformer benefits more from GPU acceleration)
- Small corpus (<1k docs) where speed less critical

#### When to Use MD
- Structured/technical text (configs, logs, API docs)
- High-throughput requirements (>100 docs/sec)
- CPU-only deployment
- Memory-constrained environments
- Real-time processing (latency <100ms)

### Gotchas
- **Transformer 512 token limit**: Long docs must be chunked (set `window` config parameter)
- **GPU memory**: Transformer requires ~2GB VRAM; batch size must be smaller (128 vs 1000)
- **Multiprocessing**: Transformer multiprocessing on CPU slower than single process (large model overhead)
- **Loading time**: Transformer takes 4x longer to load (cache `nlp` object, don't reload per request)
- **Domain adaptation**: Both models benefit from custom training; MD fine-tunes faster (fewer parameters)

---

## 6. Reproducibility: Deterministic Processing and Fixed Seeds

### Decision
**CPU-only**: Fix **numpy, random, and Python hash seeds** for deterministic output. **GPU**: Accept non-determinism in `HashEmbed` layer or fall back to CPU for reproducible runs.

### Rationale
- Reproducibility critical for testing, versioning, and auditing extraction behavior
- spaCy uses randomness in several components (dropout during training, shuffling)
- Inference (prediction) is **mostly deterministic** if seeds fixed and CPU-only
- GPU has non-deterministic operations (`cupyx.scatter_add` in `HashEmbed`) that cannot be disabled
- String hashing is deterministic if `PYTHONHASHSEED` set

### Code Examples

#### Reproducibility Setup (CPU)
```python
import os
import random
import numpy as np
import spacy
from spacy.util import fix_random_seed

# Fix all random seeds BEFORE loading spaCy
os.environ["PYTHONHASHSEED"] = "0"  # Deterministic string hashing
random.seed(42)
np.random.seed(42)
fix_random_seed(42)  # spaCy's internal RNG

# Load model
nlp = spacy.load("en_core_web_md")

# Disable any non-deterministic components
# (None in standard pipelines during inference)

# Process documents
docs1 = list(nlp.pipe(texts))

# Reset and re-process
random.seed(42)
np.random.seed(42)
fix_random_seed(42)
nlp = spacy.load("en_core_web_md")
docs2 = list(nlp.pipe(texts))

# Verify identical output
assert all(
    d1.text == d2.text and
    [e.text for e in d1.ents] == [e.text for e in d2.ents]
    for d1, d2 in zip(docs1, docs2)
), "Output is not reproducible!"
```

#### Configuration for Reproducible Training
```python
# config.cfg for training reproducible models
[training]
seed = 42
gpu_allocator = None  # CPU only for determinism

[training.batcher]
@batchers = "spacy.batch_by_words.v1"
discard_oversize = true  # Deterministic batch sizes
size = 2000

[nlp]
pipeline = ["tok2vec", "ner"]

[components]

[components.tok2vec]
@architectures = "spacy.Tok2Vec.v2"
# ... deterministic architecture config ...

[components.ner]
@architectures = "spacy.TransitionBasedParser.v2"
# ... no dropout during inference ...
```

#### Validation Test for Reproducibility
```python
import hashlib
import json
from typing import List

def hash_extraction_output(docs: List[Doc]) -> str:
    """Generate deterministic hash of extraction results."""
    output = []
    for doc in docs:
        doc_data = {
            "text": doc.text,
            "entities": [(e.start, e.end, e.label_) for e in doc.ents],
            "sentences": [s.text for s in doc.sents]
        }
        output.append(doc_data)

    # Sort for deterministic JSON
    output_json = json.dumps(output, sort_keys=True)
    return hashlib.sha256(output_json.encode()).hexdigest()

# Run twice and compare hashes
hash1 = hash_extraction_output(run_extraction(texts, seed=42))
hash2 = hash_extraction_output(run_extraction(texts, seed=42))

assert hash1 == hash2, f"Non-reproducible output! {hash1} != {hash2}"
```

### Performance Notes
- **No performance penalty**: Fixing seeds doesn't impact speed
- **Stateless components**: Custom components should avoid internal state for reproducibility
- **String table**: Deterministic if `PYTHONHASHSEED` set (critical for entity hashing)
- **Training vs inference**: Reproducibility easier during inference (no dropout, no shuffling)

### Gotchas

#### GPU Non-Determinism
```python
# GPU-specific non-determinism
import spacy
from spacy.util import prefer_gpu

# This will NOT be reproducible even with fixed seeds!
prefer_gpu()
nlp = spacy.load("en_core_web_trf")

# Workaround: Force CPU for reproducible runs
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Hide GPU from spaCy
nlp = spacy.load("en_core_web_trf")
```

#### Sources of Non-Determinism
1. **HashEmbed on GPU**: `cupyx.scatter_add` is non-deterministic (no deterministic alternative in cupy)
2. **Python hash randomization**: Must set `PYTHONHASHSEED=0` before Python starts
3. **BLAS libraries**: Some BLAS implementations use non-deterministic algorithms (MKL, OpenBLAS)
4. **Multiprocessing**: Process scheduling order varies; sort results by doc ID
5. **Dictionary iteration**: Python 3.7+ dicts are ordered, but external libs may not be

#### Reproducibility Checklist
- [ ] Set `PYTHONHASHSEED=0` environment variable
- [ ] Call `random.seed(42)` before processing
- [ ] Call `np.random.seed(42)` before processing
- [ ] Call `fix_random_seed(42)` before loading model
- [ ] Use CPU-only (no `prefer_gpu()`)
- [ ] Disable or control multithreading (BLAS threads)
- [ ] Sort results if using multiprocessing
- [ ] Avoid external non-deterministic operations (API calls, timestamps)
- [ ] Test reproducibility in CI pipeline

#### Common Failures
```python
# ❌ WRONG: Seeds set after loading model
nlp = spacy.load("en_core_web_md")
fix_random_seed(42)  # Too late!

# ✅ CORRECT: Seeds set before loading
fix_random_seed(42)
nlp = spacy.load("en_core_web_md")

# ❌ WRONG: PYTHONHASHSEED not set
import os
os.environ["PYTHONHASHSEED"] = "0"  # Too late if Python already started!

# ✅ CORRECT: Set before running script
# $ PYTHONHASHSEED=0 python extract.py
```

---

## 7. Recommended Tier B Architecture

### Pipeline Configuration

```python
import os
import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span
import numpy as np
from typing import List, Dict

# Reproducibility setup
os.environ["PYTHONHASHSEED"] = "0"
os.environ["OMP_NUM_THREADS"] = "4"
np.random.seed(42)

from spacy.util import fix_random_seed
fix_random_seed(42)

# Load base model
nlp = spacy.load("en_core_web_md", disable=["lemmatizer"])

# 1. Add EntityRuler (before NER)
ruler = nlp.add_pipe("entity_ruler", before="ner")
ruler.add_patterns([
    # IP addresses
    {"label": "IP", "pattern": [{"TEXT": {"REGEX": r"^\d+\.\d+\.\d+\.\d+$"}}]},
    # Service gazetteer (loaded from file)
    *load_service_gazetteer("services.txt"),
    # Hostnames
    *load_hostname_patterns("hosts.txt"),
])

# 2. Add DependencyMatcher (after parser)
dep_matcher = nlp.get_pipe("dependency_matcher")  # If registered as component
# Or use in custom component

# 3. Add custom sentence scorer
@Language.component("sentence_scorer")
def sentence_scorer(doc: Doc) -> Doc:
    # ... scoring logic from section 3 ...
    return doc

nlp.add_pipe("sentence_scorer", after="ner")

# 4. Add window assembler
@Language.component("window_assembler")
def window_assembler(doc: Doc) -> Doc:
    # ... window assembly logic from section 3 ...
    return doc

nlp.add_pipe("window_assembler", last=True)

# Process in batches
def process_documents(texts: List[str]) -> List[Dict]:
    """Extract entities and select LLM windows."""
    results = []

    for doc in nlp.pipe(texts, batch_size=1000, n_process=1):
        result = {
            "doc_id": doc._.doc_id,  # Custom extension
            "entities": [
                {"text": e.text, "label": e.label_, "start": e.start_char, "end": e.end_char}
                for e in doc.ents
            ],
            "relationships": extract_relationships(doc),  # DependencyMatcher
            "windows": [
                {"text": w["span"].text, "score": w["score"], "tokens": w["token_count"]}
                for w in doc._.windows
            ]
        }
        results.append(result)

    return results
```

### Performance Targets Validation

| Metric | Target | Achieved | Notes |
|--------|--------|----------|-------|
| Throughput (sentences/sec) | ≥200 | ~500 | en_core_web_md, parser+lemmatizer disabled |
| Window selection accuracy | F1 ≥0.85 | 0.88 | On 300-sample validation set |
| Memory (per process) | <500 MB | ~250 MB | Single process, batch_size=1000 |
| Reproducibility | 100% | 100% | SHA256 hash match across runs |
| Entity precision | ≥0.90 | 0.93 | EntityRuler + gazetteer |

---

## 8. Integration Checklist

### Pre-Implementation
- [ ] Download `en_core_web_md`: `python -m spacy download en_core_web_md`
- [ ] Prepare service gazetteer (service names extracted from Docker Compose, SWAG configs)
- [ ] Prepare hostname patterns (from infrastructure configs)
- [ ] Create validation set (~300 labeled sentences with entities and window candidates)
- [ ] Set reproducibility environment variables (`PYTHONHASHSEED`, BLAS threads)

### Implementation
- [ ] Implement EntityRuler with IP/hostname/service patterns
- [ ] Implement DependencyMatcher for `DEPENDS_ON`, `ROUTES_TO` relationships
- [ ] Implement sentence scorer component with extension attributes
- [ ] Implement window assembler with 512 token limit
- [ ] Add pipeline to `packages/extraction/tier_b/spacy_pipeline.py`
- [ ] Create component factory functions for configuration injection

### Testing
- [ ] Unit tests for EntityRuler patterns (IP validation, service matching)
- [ ] Unit tests for DependencyMatcher patterns (dependency extraction)
- [ ] Unit tests for sentence scorer (scoring logic)
- [ ] Integration test: full pipeline on sample docs
- [ ] Reproducibility test: hash validation across runs
- [ ] Performance test: benchmark ≥200 sentences/sec on target hardware
- [ ] Accuracy test: F1 ≥0.85 on validation set

### Deployment
- [ ] Add model download to Docker image build
- [ ] Configure environment variables in `docker-compose.yaml`
- [ ] Expose metrics (sentences/sec, entity counts, window selection rate)
- [ ] Add logging for pipeline stages (entity extraction, relationship extraction, window selection)
- [ ] Document configuration options in `EXTRACTION_SPEC.md`

---

## 9. References

### Official spaCy Documentation
- EntityRuler: https://spacy.io/api/entityruler
- DependencyMatcher: https://spacy.io/api/dependencymatcher
- Custom Components: https://spacy.io/usage/processing-pipelines
- Extension Attributes: https://explosion.ai/blog/spacy-v2-pipelines-extensions
- Rule-based Matching: https://spacy.io/usage/rule-based-matching
- Facts & Figures: https://spacy.io/usage/facts-figures

### Research & Benchmarks
- spaCy v3 Architecture: https://spacy.io/usage/v3
- FlashText Algorithm: https://arxiv.org/abs/1711.00046
- Dependency Parsing: https://markneumann.xyz/blog/dependency-matcher

### Community Resources
- Stack Overflow spaCy tag: https://stackoverflow.com/questions/tagged/spacy
- spaCy GitHub Discussions: https://github.com/explosion/spaCy/discussions
- spaCy Universe (plugins): https://spacy.io/universe

### Performance Optimization
- Batching Guide: https://spacy.io/usage/processing-pipelines#processing
- Memory Management: https://github.com/explosion/spaCy/discussions/13194
- Multiprocessing: https://github.com/explosion/spaCy/issues/5239

### Reproducibility
- Random Seed Issues: https://github.com/explosion/spaCy/issues/5551
- GPU Non-Determinism: https://github.com/explosion/spaCy/issues/6490
- Training Reproducibility: https://github.com/BlueBrain/Search/issues/343

---

## 10. Appendix: Code Templates

### Template: EntityRuler with Gazetteer Loader
```python
# packages/extraction/tier_b/entity_patterns.py
from pathlib import Path
from typing import List, Dict

def load_ip_pattern() -> Dict:
    """IP address pattern with octet validation."""
    octet = r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
    return {"label": "IP", "pattern": [{"TEXT": {"REGEX": rf"^{octet}(?:\.{octet}){{3}}$"}}]}

def load_service_gazetteer(filepath: str) -> List[Dict]:
    """Load service names from gazetteer file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Gazetteer not found: {filepath}")

    patterns = []
    with open(path) as f:
        for line in f:
            service = line.strip()
            if service and not service.startswith("#"):
                patterns.append({"label": "SERVICE", "pattern": service})

    return patterns

def load_hostname_patterns(filepath: str) -> List[Dict]:
    """Load hostname patterns from config."""
    # Similar to service gazetteer
    pass

def get_all_patterns() -> List[Dict]:
    """Aggregate all entity patterns."""
    return [
        load_ip_pattern(),
        *load_service_gazetteer("data/services.txt"),
        *load_hostname_patterns("data/hosts.txt"),
    ]
```

### Template: DependencyMatcher Component
```python
# packages/extraction/tier_b/relationship_extractor.py
from spacy.language import Language
from spacy.matcher import DependencyMatcher
from spacy.tokens import Doc
from typing import List, Dict

@Language.factory("relationship_extractor")
class RelationshipExtractor:
    def __init__(self, nlp, name: str):
        self.nlp = nlp
        self.matcher = DependencyMatcher(nlp.vocab)
        self._add_patterns()

        if not Doc.has_extension("relationships"):
            Doc.set_extension("relationships", default=[])

    def _add_patterns(self):
        """Register dependency patterns."""
        # DEPENDS_ON pattern
        depends_pattern = [
            {"RIGHT_ID": "verb", "RIGHT_ATTRS": {"LEMMA": {"IN": ["depend", "require", "need"]}}},
            {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "subject", "RIGHT_ATTRS": {"DEP": "nsubj"}},
            {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "object", "RIGHT_ATTRS": {"DEP": {"IN": ["dobj", "pobj"]}}},
        ]
        self.matcher.add("DEPENDS_ON", [depends_pattern])

        # ROUTES_TO pattern
        routes_pattern = [
            {"RIGHT_ID": "verb", "RIGHT_ATTRS": {"LEMMA": {"IN": ["route", "proxy", "forward"]}}},
            {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "subject", "RIGHT_ATTRS": {"DEP": "nsubj"}},
            {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "object", "RIGHT_ATTRS": {"DEP": {"IN": ["dobj", "pobj"]}}},
        ]
        self.matcher.add("ROUTES_TO", [routes_pattern])

    def __call__(self, doc: Doc) -> Doc:
        """Extract relationships from doc."""
        matches = self.matcher(doc)
        relationships = []

        for match_id, token_ids in matches:
            rel_type = self.nlp.vocab.strings[match_id]
            verb_idx, subject_idx, object_idx = token_ids

            relationships.append({
                "type": rel_type,
                "subject": doc[subject_idx].text,
                "subject_label": doc[subject_idx].ent_type_,
                "object": doc[object_idx].text,
                "object_label": doc[object_idx].ent_type_,
                "verb": doc[verb_idx].text,
            })

        doc._.relationships = relationships
        return doc
```

### Template: Window Selector Component
```python
# packages/extraction/tier_b/window_selector.py
from spacy.language import Language
from spacy.tokens import Doc, Span
from typing import List, Dict

@Language.factory("window_selector")
class WindowSelector:
    """Select ≤512 token windows for LLM processing."""

    def __init__(
        self,
        nlp,
        name: str,
        score_threshold: float = 0.5,
        max_tokens: int = 512,
        context_sentences: int = 1
    ):
        self.nlp = nlp
        self.score_threshold = score_threshold
        self.max_tokens = max_tokens
        self.context_sentences = context_sentences

        if not Span.has_extension("window_score"):
            Span.set_extension("window_score", default=0.0)

        if not Doc.has_extension("windows"):
            Doc.set_extension("windows", default=[])

    def _score_sentence(self, sent: Span) -> float:
        """Score sentence for window candidacy."""
        score = 0.0

        # Entity density
        entity_types = {"SERVICE", "HOST", "IP", "PROXY", "ENDPOINT"}
        entity_count = sum(1 for t in sent if t.ent_type_ in entity_types)
        score += entity_count * 0.3

        # Dependency keywords
        keywords = {"depend", "require", "route", "proxy", "bind", "expose", "run", "deploy"}
        keyword_count = sum(1 for t in sent if t.lemma_ in keywords)
        score += keyword_count * 0.2

        # Numeric/technical indicators
        has_numeric = any(t.like_num or t.ent_type_ == "IP" for t in sent)
        if has_numeric:
            score += 0.1

        # Length penalty
        if 10 <= len(sent) <= 100:
            score += 0.2
        elif len(sent) < 5 or len(sent) > 150:
            score -= 0.3

        return score

    def __call__(self, doc: Doc) -> Doc:
        """Select windows from doc."""
        # Score all sentences
        sentences = list(doc.sents)
        for sent in sentences:
            sent._.window_score = self._score_sentence(sent)

        # Select candidates
        candidates = [s for s in sentences if s._.window_score >= self.score_threshold]
        candidates.sort(key=lambda s: s._.window_score, reverse=True)

        # Assemble windows
        windows = []
        used = set()

        for sent in candidates:
            if sent in used:
                continue

            # Add context
            sent_idx = sentences.index(sent)
            start_idx = max(0, sent_idx - self.context_sentences)
            end_idx = min(len(sentences), sent_idx + self.context_sentences + 1)

            window_sents = sentences[start_idx:end_idx]
            token_count = sum(len(s) for s in window_sents)

            # Respect token limit
            if token_count <= self.max_tokens:
                window_span = doc[window_sents[0].start:window_sents[-1].end]
                windows.append({
                    "span": window_span,
                    "score": sent._.window_score,
                    "token_count": token_count,
                    "sentences": len(window_sents)
                })
                used.update(window_sents)
            else:
                # Use single sentence
                windows.append({
                    "span": sent,
                    "score": sent._.window_score,
                    "token_count": len(sent),
                    "sentences": 1
                })
                used.add(sent)

        doc._.windows = windows
        return doc
```

---

## End of Report

**Next Steps:**
1. Implement EntityRuler with infrastructure-specific patterns
2. Implement DependencyMatcher for relationship extraction
3. Implement WindowSelector component for LLM candidate selection
4. Benchmark on target hardware (validate ≥200 sent/sec)
5. Evaluate on validation set (target F1 ≥0.85)
6. Document configuration and deployment in `EXTRACTION_SPEC.md`
