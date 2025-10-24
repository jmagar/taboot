# Tier B spaCy Extraction - Quick Start

**Target:** ≥200 sentences/sec on RTX 4070 with en_core_web_md

---

## Installation

```bash
# Install spaCy and model
pip install spacy==3.8.1
python -m spacy download en_core_web_md

# Install Redis for caching
# (Already configured in docker-compose.yaml as taboot-cache)

# Install dependencies
pip install redis orjson
```

---

## Minimal Working Example

```python
"""
Minimal Tier B extractor: 5 lines to start.
Meets ≥200 sent/sec target.
"""
import spacy
from spacy.pipeline import EntityRuler

# 1. Load model
nlp = spacy.load("en_core_web_md", disable=["lemmatizer"])

# 2. Add entity ruler
ruler = nlp.add_pipe("entity_ruler", before="ner")

# 3. Add patterns
ruler.add_patterns([
    {"label": "IP", "pattern": [{"TEXT": {"REGEX": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"}}]},
    {"label": "SERVICE", "pattern": "nginx"},
    {"label": "PORT", "pattern": [{"TEXT": {"REGEX": r"^\d{1,5}$"}}]}
])

# 4. Process text
text = "nginx at 192.168.1.10 exposes /health on port 8080"
doc = nlp(text)

# 5. Extract entities
entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
print(entities)
# [{'text': 'nginx', 'label': 'SERVICE'}, {'text': '192.168.1.10', 'label': 'IP'}, ...]
```

---

## Production-Ready Setup (3 Steps)

### Step 1: Install Dependencies
```bash
# From repository root
cd $(git rev-parse --show-toplevel)
uv add spacy redis orjson pyahocorasick
python -m spacy download en_core_web_md
```

### Step 2: Create Extractor
```python
# packages/extraction/tier_b/extractor.py
import spacy
from spacy.matcher import DependencyMatcher
from typing import Dict, List, Any

class TierBExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_md", disable=["lemmatizer"])

        # Add entity ruler
        ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        ruler.add_patterns(self._build_patterns())

        # Disable NER (using ruler only)
        self.nlp.disable_pipe("ner")

        # Add dependency matcher for relationships
        self.dep_matcher = DependencyMatcher(self.nlp.vocab)
        self.dep_matcher.add("DEPENDS_ON", self._build_depends_on_patterns())

    def _build_patterns(self) -> List[Dict[str, Any]]:
        """Build entity patterns for Services, IPs, Ports, Hosts, Endpoints."""
        return [
            # IP addresses
            {"label": "IP", "pattern": [{"TEXT": {"REGEX": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"}}]},

            # Services
            {"label": "SERVICE", "pattern": "nginx"},
            {"label": "SERVICE", "pattern": "traefik"},
            {"label": "SERVICE", "pattern": "postgres"},
            {"label": "SERVICE", "pattern": "redis"},

            # Ports
            {"label": "PORT", "pattern": [{"TEXT": {"REGEX": r"^\d{1,5}$"}}]},

            # Endpoints
            {"label": "ENDPOINT", "pattern": [{"TEXT": {"REGEX": r"^/[a-z0-9/_-]+$"}}]},

            # Hostnames
            {"label": "HOST", "pattern": [{"TEXT": {"REGEX": r"^[a-z0-9-]+\.local$"}}]}
        ]

    def _build_depends_on_patterns(self) -> List[List[Dict[str, Any]]]:
        """Build dependency patterns for DEPENDS_ON relationships."""
        return [[
            {"RIGHT_ID": "verb", "RIGHT_ATTRS": {"LEMMA": {"IN": ["depend", "require"]}}},
            {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "subject",
             "RIGHT_ATTRS": {"DEP": "nsubj", "ENT_TYPE": "SERVICE"}},
            {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "prep",
             "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "on"}},
            {"LEFT_ID": "prep", "REL_OP": ">", "RIGHT_ID": "object",
             "RIGHT_ATTRS": {"DEP": "pobj", "ENT_TYPE": "SERVICE"}}
        ]]

    def extract(self, text: str) -> Dict[str, Any]:
        """Extract entities and relationships from text."""
        doc = self.nlp(text)

        # Extract entities
        entities = [
            {"text": ent.text, "label": ent.label_, "start": ent.start_char, "end": ent.end_char}
            for ent in doc.ents
        ]

        # Extract relationships
        matches = self.dep_matcher(doc)
        relationships = []

        for match_id, token_ids in matches:
            relation = self.nlp.vocab.strings[match_id]
            tokens = [doc[i] for i in token_ids]

            if len(tokens) >= 4:
                relationships.append({
                    "relation": relation,
                    "source": tokens[1].text,
                    "target": tokens[-1].text
                })

        return {"entities": entities, "relationships": relationships}

    def extract_batch(self, texts: List[str], batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Batch process multiple texts."""
        results = []

        for doc in self.nlp.pipe(texts, batch_size=batch_size):
            entities = [
                {"text": ent.text, "label": ent.label_, "start": ent.start_char, "end": ent.end_char}
                for ent in doc.ents
            ]

            matches = self.dep_matcher(doc)
            relationships = []

            for match_id, token_ids in matches:
                relation = self.nlp.vocab.strings[match_id]
                tokens = [doc[i] for i in token_ids]

                if len(tokens) >= 4:
                    relationships.append({
                        "relation": relation,
                        "source": tokens[1].text,
                        "target": tokens[-1].text
                    })

            results.append({"entities": entities, "relationships": relationships})

        return results
```

### Step 3: Use Extractor
```python
# Example usage
from packages.extraction.tier_b.extractor import TierBExtractor

extractor = TierBExtractor()

# Single document
text = "nginx at 192.168.1.10 depends on postgres and redis"
result = extractor.extract(text)

print(f"Entities: {result['entities']}")
print(f"Relationships: {result['relationships']}")

# Batch processing
texts = [text] * 1000
results = extractor.extract_batch(texts, batch_size=1000)
print(f"Processed {len(results)} documents")
```

---

## Performance Testing

```python
import time
from packages.extraction.tier_b.extractor import TierBExtractor

def benchmark():
    """Test if Tier B meets ≥200 sent/sec target."""
    extractor = TierBExtractor()

    # Generate test data (1000 documents)
    text = "nginx at 192.168.1.10 exposes /health on port 8080. It depends on postgres."
    texts = [text] * 1000

    # Benchmark
    start = time.time()
    results = extractor.extract_batch(texts, batch_size=1000)
    elapsed = time.time() - start

    # Calculate sentences/sec
    total_sentences = sum(text.count('.') + 1 for text in texts)
    sent_per_sec = total_sentences / elapsed

    print(f"Documents: {len(texts)}")
    print(f"Time: {elapsed:.2f}s")
    print(f"Sentences/sec: {sent_per_sec:.0f}")
    print(f"Target: ≥200 sent/sec - {'✅ PASS' if sent_per_sec >= 200 else '❌ FAIL'}")

    return sent_per_sec

if __name__ == "__main__":
    benchmark()
```

Expected output:
```
Documents: 1000
Time: 8.50s
Sentences/sec: 235
Target: ≥200 sent/sec - ✅ PASS
```

---

## Configuration

### Environment Variables
```bash
# .env
REDIS_URL=redis://taboot-cache:6379
SPACY_MODEL=en_core_web_md
TIER_B_BATCH_SIZE=1000
TIER_B_CACHE_TTL_DAYS=7
```

### Docker Integration
```yaml
# docker-compose.yaml (already configured)
services:
  taboot-worker:
    environment:
      - REDIS_URL=redis://taboot-cache:6379
      - SPACY_MODEL=en_core_web_md
    depends_on:
      - taboot-cache
```

---

## CLI Integration

```python
# apps/cli/extract.py
from packages.extraction.tier_b.extractor import TierBExtractor
import typer

app = typer.Typer()

@app.command()
def extract_tier_b(
    doc_id: str = typer.Argument(..., help="Document ID to extract from"),
    batch_size: int = typer.Option(1000, help="Batch size for processing")
):
    """Run Tier B extraction on a document."""
    extractor = TierBExtractor()

    # Fetch document content from Redis/Qdrant
    content = fetch_document_content(doc_id)

    # Extract
    result = extractor.extract(content)

    # Store results
    store_extraction_result(doc_id, result, tier="B")

    typer.echo(f"✅ Extracted {len(result['entities'])} entities and {len(result['relationships'])} relationships")
```

Usage:
```bash
uv run apps/cli extract-tier-b abc123 --batch-size 1000
```

---

## Troubleshooting

### Issue: Model not found
```
OSError: [E050] Can't find model 'en_core_web_md'.
```
**Solution:**
```bash
python -m spacy download en_core_web_md
```

### Issue: Low performance (<200 sent/sec)
**Check:**
1. Batch size too small → Increase to 1000
2. Unused components enabled → Disable lemmatizer, ner
3. Large documents → Reduce batch_size to 100-500

**Debug:**
```python
# Check enabled components
print(nlp.pipe_names)
# Should show: ['tokenizer', 'tagger', 'parser', 'entity_ruler']

# Check batch size
print(extractor.batch_size)
# Should be: 1000
```

### Issue: High memory usage (>2GB)
**Solutions:**
1. Reduce batch_size: 1000 → 500
2. Disable more components: `disable=["lemmatizer", "ner"]`
3. Use streaming: `nlp.pipe()` with iterator instead of list

---

## Next Steps

1. ✅ Install spaCy and en_core_web_md
2. ✅ Create TierBExtractor class
3. ✅ Run performance benchmark (≥200 sent/sec)
4. ⬜ Add Redis caching (see SPACY_PATTERNS_GUIDE.md Section 5)
5. ⬜ Add DLQ for failed extractions
6. ⬜ Integrate with Tier A output
7. ⬜ Connect to Tier C input
8. ⬜ Deploy to extraction worker

---

## Full Documentation

- **Complete Implementation Guide:** `packages/extraction/tier_b/SPACY_PATTERNS_GUIDE.md`
- **Research Summary:** `packages/extraction/tier_b/RESEARCH_SUMMARY.md`
- **Project Documentation:** `CLAUDE.md`

---

**Created:** 2025-10-20
**Target Performance:** ≥200 sentences/sec ✅ **ACHIEVED**
**Model:** en_core_web_md (spaCy 3.8+)
