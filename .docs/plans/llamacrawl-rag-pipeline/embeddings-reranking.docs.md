# HuggingFace TEI Integration with LlamaIndex: Embeddings and Reranking

## Table of Contents
1. [TEI API Integration](#tei-api-integration)
2. [LlamaIndex Custom Embeddings](#llamaindex-custom-embeddings)
3. [Qwen3 Embedding Model](#qwen3-embedding-model)
4. [Reranking with TEI](#reranking-with-tei)
5. [Qwen3 Reranker Model](#qwen3-reranker-model)
6. [Complete Query Pipeline](#complete-query-pipeline)
7. [Code Examples](#code-examples)

## Overview

This document details integration patterns for HuggingFace Text Embeddings Inference (TEI) with LlamaIndex for building a production-ready RAG pipeline using Qwen3 models for both embeddings and reranking.

**Key Benefits:**
- High-performance inference with TEI
- Self-hosted embedding and reranking services
- State-of-the-art multilingual support (100+ languages)
- Flexible architecture with 32K context length
- Optimized for RAG workflows

## 1. TEI API Integration

### 1.1 Overview

Text Embeddings Inference (TEI) is HuggingFace's toolkit for deploying and serving open source text embeddings and sequence classification models with optimized performance.

**Official Documentation:**
- API Reference: https://huggingface.github.io/text-embeddings-inference/
- GitHub: https://github.com/huggingface/text-embeddings-inference
- Quick Tour: https://huggingface.co/docs/text-embeddings-inference/en/quick_tour

### 1.2 HTTP Endpoints

TEI provides three primary endpoints:

#### 1.2.1 Embed Endpoint (`/embed`)

Generates embeddings for input text(s).

**Request Format:**
```bash
curl http://127.0.0.1:8080/embed \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"inputs": "What is Deep Learning?"}'
```

**Batch Request:**
```bash
curl http://127.0.0.1:8080/embed \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"inputs": ["sentence 1", "sentence 2", "sentence 3"], "truncate": true}'
```

**Response Format:**
```json
[
  [0.334, -0.123, 0.456, ...],
  [-0.234, 0.567, -0.890, ...],
  [0.789, -0.012, 0.345, ...]
]
```

**Python Example:**
```python
import requests

API_URL = "http://localhost:8080/embed"
headers = {"Content-Type": "application/json"}

def get_embeddings(texts):
    """Generate embeddings for a list of texts."""
    response = requests.post(
        API_URL,
        headers=headers,
        json={"inputs": texts, "truncate": True}
    )
    return response.json()

# Single text
embedding = get_embeddings("What is Deep Learning?")

# Batch processing
embeddings = get_embeddings([
    "First document to embed",
    "Second document to embed",
    "Third document to embed"
])
```

#### 1.2.2 Rerank Endpoint (`/rerank`)

Ranks similarity between a query and multiple texts using cross-encoder models.

**Request Format:**
```bash
curl http://127.0.0.1:8080/rerank \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "What is Deep Learning?",
    "texts": [
      "Deep Learning is not...",
      "Deep learning is..."
    ],
    "raw_scores": false
  }'
```

**Response Format:**
```json
[
  {
    "index": 1,
    "score": 0.95
  },
  {
    "index": 0,
    "score": 0.12
  }
]
```

**Parameters:**
- `query` (string): The query text
- `texts` (array of strings): List of texts to rank against the query
- `raw_scores` (boolean): If false, returns normalized scores (0-1 range); if true, returns raw logits

**Python Example:**
```python
import requests

API_URL = "http://localhost:8080/rerank"
headers = {"Content-Type": "application/json"}

def rerank_documents(query, documents, top_n=5):
    """Rerank documents based on relevance to query."""
    response = requests.post(
        API_URL,
        headers=headers,
        json={
            "query": query,
            "texts": documents,
            "raw_scores": False
        }
    )
    results = response.json()
    # Sort by score and return top_n
    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
    return sorted_results[:top_n]

# Example usage
query = "What is machine learning?"
docs = [
    "Machine learning is a subset of AI...",
    "The weather today is sunny...",
    "ML algorithms learn from data..."
]
ranked = rerank_documents(query, docs, top_n=2)
```

#### 1.2.3 Predict Endpoint (`/predict`)

For sequence classification models (not typically used in RAG pipelines).

**Request Format:**
```bash
curl http://127.0.0.1:8080/predict \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"inputs": "I like you."}'
```

### 1.3 Deployment

**Docker Deployment (Basic):**
```bash
# Set model and volume
export MODEL_ID="Qwen/Qwen3-Embedding-0.6B"
export VOLUME=$PWD/data

# Run TEI container
docker run --gpus all -p 8080:80 \
  -v $VOLUME:/data \
  --pull always \
  ghcr.io/huggingface/text-embeddings-inference:1.8 \
  --model-id $MODEL_ID
```

**Docker Deployment (Reranker):**
```bash
# For reranker model
export MODEL_ID="Qwen/Qwen3-Reranker-0.6B"
export VOLUME=$PWD/data

docker run --gpus all -p 8080:80 \
  -v $VOLUME:/data \
  --pull always \
  ghcr.io/huggingface/text-embeddings-inference:1.8 \
  --model-id $MODEL_ID
```

**Configuration Parameters:**
- `--max-batch-tokens`: Maximum tokens per batch
- `--max-batch-requests`: Maximum requests per batch
- `--max-client-batch-size`: Default 32
- `--payload-limit`: Default 2MB (2000000 bytes)
- `--port`: Default 80

### 1.4 OpenAI-Compatible API

TEI also supports OpenAI-compatible format:

```bash
curl http://localhost:8080/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What is Deep Learning?",
    "model": "text-embeddings-inference",
    "encoding_format": "float"
  }'
```

## 2. LlamaIndex Custom Embeddings

### 2.1 Overview

LlamaIndex supports custom embedding implementations through the `BaseEmbedding` class, enabling integration with external services like TEI.

**Official Documentation:**
- Custom Embeddings: https://docs.llamaindex.ai/en/stable/examples/embeddings/custom_embeddings/
- Embeddings Guide: https://docs.llamaindex.ai/en/stable/module_guides/models/embeddings/

### 2.2 BaseEmbedding Class Structure

The `BaseEmbedding` class requires implementing five abstract methods:

```python
from typing import List
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.bridge.pydantic import PrivateAttr

class CustomEmbedding(BaseEmbedding):
    """Custom embedding class template."""

    # Required abstract methods:

    def _get_query_embedding(self, query: str) -> List[float]:
        """Synchronous query embedding."""
        pass

    def _get_text_embedding(self, text: str) -> List[float]:
        """Synchronous text embedding (single)."""
        pass

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Synchronous batch text embeddings."""
        pass

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Asynchronous query embedding."""
        pass

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Asynchronous text embedding."""
        pass

    @classmethod
    def class_name(cls) -> str:
        """Return class name for serialization."""
        return "CustomEmbedding"
```

### 2.3 TEI Embedding Implementation

Complete implementation for TEI embedding service:

```python
from typing import Any, List, Optional
import requests
import asyncio
import aiohttp
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.bridge.pydantic import PrivateAttr


class TEIEmbedding(BaseEmbedding):
    """Custom embedding class for HuggingFace Text Embeddings Inference (TEI)."""

    _base_url: str = PrivateAttr()
    _timeout: int = PrivateAttr()
    _truncate: bool = PrivateAttr()

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        model_name: str = "text-embeddings-inference",
        embed_batch_size: int = 32,
        timeout: int = 60,
        truncate: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize TEI embedding client.

        Args:
            base_url: TEI service endpoint URL
            model_name: Model name for tracking
            embed_batch_size: Batch size for encoding
            timeout: Request timeout in seconds
            truncate: Whether to truncate long texts
        """
        super().__init__(
            model_name=model_name,
            embed_batch_size=embed_batch_size,
            **kwargs
        )
        self._base_url = base_url.rstrip('/')
        self._timeout = timeout
        self._truncate = truncate

    @classmethod
    def class_name(cls) -> str:
        return "TEIEmbedding"

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Internal method to get embeddings from TEI service."""
        url = f"{self._base_url}/embed"
        headers = {"Content-Type": "application/json"}
        payload = {
            "inputs": texts,
            "truncate": self._truncate
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"TEI embedding request failed: {str(e)}")

    async def _aembed_texts(self, texts: List[str]) -> List[List[float]]:
        """Async internal method to get embeddings from TEI service."""
        url = f"{self._base_url}/embed"
        headers = {"Content-Type": "application/json"}
        payload = {
            "inputs": texts,
            "truncate": self._truncate
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            raise RuntimeError(f"TEI embedding request failed: {str(e)}")

    def _get_query_embedding(self, query: str) -> List[float]:
        """Get embedding for a single query."""
        embeddings = self._embed_texts([query])
        return embeddings[0]

    def _get_text_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text."""
        embeddings = self._embed_texts([text])
        return embeddings[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts (batch)."""
        return self._embed_texts(texts)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Async get embedding for a single query."""
        embeddings = await self._aembed_texts([query])
        return embeddings[0]

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Async get embedding for a single text."""
        embeddings = await self._aembed_texts([text])
        return embeddings[0]


# Usage example
embed_model = TEIEmbedding(
    base_url="http://localhost:8080",
    model_name="Qwen3-Embedding-0.6B",
    embed_batch_size=32,
    timeout=60,
    truncate=True
)

# Generate embeddings
text = "What is machine learning?"
embedding = embed_model.get_text_embedding(text)
print(f"Embedding dimension: {len(embedding)}")

# Batch embeddings
texts = ["First document", "Second document", "Third document"]
embeddings = embed_model.get_text_embeddings(texts)
print(f"Generated {len(embeddings)} embeddings")
```

### 2.4 Integration with LlamaIndex

**Using Custom Embeddings in LlamaIndex:**

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings

# Set custom embedding model globally
Settings.embed_model = TEIEmbedding(
    base_url="http://localhost:8080",
    model_name="Qwen3-Embedding-0.6B"
)

# Load and index documents
documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)

# Query with custom embeddings
query_engine = index.as_query_engine()
response = query_engine.query("What is the main topic?")
```

**Using with ServiceContext (Legacy):**

```python
from llama_index.core import ServiceContext, VectorStoreIndex

# Create service context with custom embeddings
service_context = ServiceContext.from_defaults(
    embed_model=TEIEmbedding(base_url="http://localhost:8080")
)

# Use in indexing
index = VectorStoreIndex.from_documents(
    documents,
    service_context=service_context
)
```

## 3. Qwen3 Embedding Model

### 3.1 Model Specifications

**Official Resources:**
- Model Card: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- GitHub: https://github.com/QwenLM/Qwen3-Embedding
- Blog Post: https://qwenlm.github.io/blog/qwen3-embedding/

**Model Variants:**

| Model | Parameters | Embedding Dim | Max Seq Len | MTEB Score |
|-------|-----------|---------------|-------------|------------|
| Qwen3-Embedding-0.6B | 0.6B | 1024 | 32K | Competitive |
| Qwen3-Embedding-4B | 4B | 2560 | 32K | High |
| Qwen3-Embedding-8B | 8B | 4096 | 32K | 70.58 (Rank #1) |

**Key Features:**
- **Multilingual**: 100+ languages supported
- **Long Context**: 32K token context length
- **MRL Support**: Matryoshka Representation Learning for flexible dimensions
- **Instruction-Aware**: Supports task-specific instructions
- **Architecture**: Dual-encoder with final [EOS] token pooling

### 3.2 Technical Details

**Embedding Dimensions:**
- Qwen3-Embedding-0.6B: 1024-dimensional vectors
- Supports user-defined output dimensions via MRL
- L2 normalization recommended for similarity calculations

**Performance Characteristics:**
- State-of-the-art on MTEB multilingual leaderboard
- Excellent cross-lingual retrieval
- Strong code retrieval capabilities
- Competitive with larger models (gte-Qwen2-7B-instruct)

**Context and Instructions:**
- Task-specific instructions can improve performance by 1-5%
- Instructions provided via prompt templates
- Recommended to use instructions on query side

### 3.3 Usage with Sentence Transformers

**Basic Usage:**
```python
from sentence_transformers import SentenceTransformer

# Load model
model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

# Define queries and documents
queries = [
    "What is the capital of China?",
    "Explain gravity",
]
documents = [
    "The capital of China is Beijing.",
    "Gravity is a force that attracts two bodies towards each other.",
]

# Generate embeddings
query_embeddings = model.encode(queries, prompt_name="query")
document_embeddings = model.encode(documents)

# Compute similarity
similarity = model.similarity(query_embeddings, document_embeddings)
print(similarity)
```

**Advanced Usage with Flash Attention:**
```python
from sentence_transformers import SentenceTransformer

# Initialize with optimizations
model = SentenceTransformer(
    "Qwen/Qwen3-Embedding-0.6B",
    model_kwargs={
        "attn_implementation": "flash_attention_2",
        "device_map": "auto"
    },
    tokenizer_kwargs={
        "padding_side": "left"
    },
    trust_remote_code=True
)

# Encode with prompts
query_embeddings = model.encode(
    queries,
    prompt_name="query",  # Uses model.prompts["query"]
    normalize_embeddings=True
)

document_embeddings = model.encode(
    documents,
    normalize_embeddings=True
)
```

### 3.4 Usage with Transformers

**Direct Transformers Usage:**
```python
import torch
from transformers import AutoTokenizer, AutoModel

# Load model and tokenizer
tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen3-Embedding-0.6B')
model = AutoModel.from_pretrained(
    'Qwen/Qwen3-Embedding-0.6B',
    torch_dtype=torch.float16,
    device_map="auto"
)

def get_embeddings(texts, max_length=32768):
    """Generate embeddings using Transformers."""
    # Tokenize
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt"
    )
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    # Generate embeddings
    with torch.no_grad():
        outputs = model(**inputs)
        # Use [EOS] token embedding
        embeddings = outputs.last_hidden_state[:, -1, :]

    # Normalize
    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

    return embeddings.cpu().numpy()

# Usage
texts = ["Sample text 1", "Sample text 2"]
embeddings = get_embeddings(texts)
print(f"Shape: {embeddings.shape}")  # (2, 1024)
```

### 3.5 Deployment with TEI

**Docker Deployment:**
```bash
# Deploy Qwen3-Embedding-0.6B with TEI
docker run --gpus all -p 8080:80 \
  -v $PWD/data:/data \
  --pull always \
  ghcr.io/huggingface/text-embeddings-inference:1.8 \
  --model-id Qwen/Qwen3-Embedding-0.6B \
  --max-batch-tokens 16384 \
  --max-client-batch-size 32
```

**Health Check:**
```bash
# Check service health
curl http://localhost:8080/health

# Get model info
curl http://localhost:8080/info
```

## 4. Reranking with TEI

### 4.1 Overview

Reranking is a critical component in RAG pipelines that improves retrieval quality by re-scoring initially retrieved documents using more sophisticated models (cross-encoders).

**Benefits of Reranking:**
- Improves relevance of top-k results
- Uses cross-encoder architecture (more accurate than bi-encoders)
- Reduces noise in final context
- Better semantic understanding
- Typical improvement: 5-15% in downstream task performance

**Resources:**
- TEI Rerank Integration: https://docs.llamaindex.ai/en/stable/api_reference/postprocessor/tei_rerank/
- LlamaHub Integration: https://llamahub.ai/l/postprocessor/llama-index-postprocessor-tei-rerank

### 4.2 TEI Reranker API

**Endpoint:** `POST /rerank`

**Request Schema:**
```typescript
{
  query: string,           // The search query
  texts: string[],         // Array of texts to rank
  raw_scores?: boolean     // Optional: return raw logits vs normalized scores
}
```

**Response Schema:**
```typescript
Array<{
  index: number,          // Original position in input array
  score: number           // Relevance score (0-1 if normalized)
}>
```

**Python Client:**
```python
import requests
from typing import List, Dict, Tuple

class TEIReranker:
    """Client for TEI reranking endpoint."""

    def __init__(self, base_url: str = "http://localhost:8080", timeout: int = 60):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = None,
        raw_scores: bool = False
    ) -> List[Dict[str, any]]:
        """Rerank documents based on query relevance.

        Args:
            query: Search query
            documents: List of document texts to rank
            top_n: Return only top N results (None = all)
            raw_scores: Return raw logits instead of normalized scores

        Returns:
            List of dicts with 'index', 'score', and 'text' keys
        """
        url = f"{self.base_url}/rerank"
        headers = {"Content-Type": "application/json"}
        payload = {
            "query": query,
            "texts": documents,
            "raw_scores": raw_scores
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            results = response.json()

            # Sort by score (highest first)
            results = sorted(results, key=lambda x: x['score'], reverse=True)

            # Add original text to results
            for result in results:
                result['text'] = documents[result['index']]

            # Return top_n if specified
            return results[:top_n] if top_n else results

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"TEI rerank request failed: {str(e)}")

    def rerank_with_texts(
        self,
        query: str,
        documents: List[Tuple[str, any]],
        top_n: int = None
    ) -> List[Tuple[str, any, float]]:
        """Rerank documents with metadata.

        Args:
            query: Search query
            documents: List of (text, metadata) tuples
            top_n: Return only top N results

        Returns:
            List of (text, metadata, score) tuples
        """
        texts = [doc[0] for doc in documents]
        results = self.rerank(query, texts, top_n=top_n)

        return [
            (result['text'], documents[result['index']][1], result['score'])
            for result in results
        ]

# Usage example
reranker = TEIReranker(base_url="http://localhost:8081")

query = "What is machine learning?"
docs = [
    "Machine learning is a subset of artificial intelligence...",
    "The weather forecast shows rain tomorrow...",
    "ML algorithms learn patterns from data...",
    "Python is a programming language...",
    "Deep learning uses neural networks..."
]

# Rerank and get top 3
ranked = reranker.rerank(query, docs, top_n=3)

for i, result in enumerate(ranked):
    print(f"{i+1}. Score: {result['score']:.4f}")
    print(f"   Text: {result['text'][:50]}...")
```

### 4.3 LlamaIndex TEI Reranker Integration

**Installation:**
```bash
pip install llama-index-postprocessor-tei-rerank
```

**Basic Usage:**
```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.postprocessor.tei_rerank import TEIRerank

# Load documents and build index
documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)

# Initialize TEI reranker
tei_rerank = TEIRerank(
    base_url="http://localhost:8081",  # TEI reranker service URL
    top_n=5  # Number of top results to return after reranking
)

# Create query engine with reranker
query_engine = index.as_query_engine(
    similarity_top_k=20,  # Retrieve more candidates initially
    node_postprocessors=[tei_rerank]  # Apply reranking
)

# Query
response = query_engine.query("What is the main topic of machine learning?")
print(response)
```

**Advanced Configuration:**
```python
from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.postprocessor.tei_rerank import TEIRerank

# Create retriever
retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=20
)

# Create reranker
reranker = TEIRerank(
    base_url="http://localhost:8081",
    top_n=5,
    timeout=30
)

# Create query engine with explicit components
query_engine = RetrieverQueryEngine(
    retriever=retriever,
    node_postprocessors=[reranker]
)

# Query
response = query_engine.query("Your query here")
```

### 4.4 Custom Reranker Implementation

If you need more control, you can implement a custom reranker:

```python
from typing import List, Optional
import requests
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

class CustomTEIRerank(BaseNodePostprocessor):
    """Custom TEI reranker postprocessor."""

    base_url: str
    top_n: int = 5
    timeout: int = 60

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        top_n: int = 5,
        timeout: int = 60,
        **kwargs
    ):
        super().__init__(
            base_url=base_url,
            top_n=top_n,
            timeout=timeout,
            **kwargs
        )

    @classmethod
    def class_name(cls) -> str:
        return "CustomTEIRerank"

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Rerank nodes based on query relevance."""
        if not query_bundle:
            return nodes

        # Extract texts from nodes
        texts = [node.node.get_content() for node in nodes]

        # Call TEI rerank API
        url = f"{self.base_url}/rerank"
        headers = {"Content-Type": "application/json"}
        payload = {
            "query": query_bundle.query_str,
            "texts": texts,
            "raw_scores": False
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            results = response.json()

            # Sort by score
            results = sorted(results, key=lambda x: x['score'], reverse=True)

            # Create new nodes with updated scores
            reranked_nodes = []
            for result in results[:self.top_n]:
                idx = result['index']
                node = nodes[idx]
                # Update score with reranker score
                node.score = result['score']
                reranked_nodes.append(node)

            return reranked_nodes

        except requests.exceptions.RequestException as e:
            # Fallback to original nodes on error
            print(f"Reranking failed: {e}")
            return nodes[:self.top_n]

# Usage
reranker = CustomTEIRerank(
    base_url="http://localhost:8081",
    top_n=5
)

query_engine = index.as_query_engine(
    similarity_top_k=20,
    node_postprocessors=[reranker]
)
```

## 5. Qwen3 Reranker Model

### 5.1 Model Specifications

**Official Resources:**
- Model Card: https://huggingface.co/Qwen/Qwen3-Reranker-0.6B
- Seq-Cls Variant: https://huggingface.co/tomaarsen/Qwen3-Reranker-0.6B-seq-cls
- GitHub: https://github.com/QwenLM/Qwen3-Embedding

**Model Variants:**

| Model | Parameters | Architecture | Max Seq Len |
|-------|-----------|--------------|-------------|
| Qwen3-Reranker-0.6B | 0.6B | Language Model (token logits) | 32K |
| Qwen3-Reranker-0.6B-seq-cls | 0.6B | Sequence Classification | 32K |
| Qwen3-Reranker-4B | 4B | Language Model (token logits) | 32K |
| Qwen3-Reranker-8B | 8B | Language Model (token logits) | 32K |

**Key Features:**
- **Architecture**: Cross-encoder based on Qwen3 foundation model
- **Multilingual**: 100+ languages
- **Long Context**: 32K tokens
- **Instruction-Aware**: Task-specific instructions supported
- **Output**: Relevance scores (0-1 normalized)

### 5.2 Architecture Differences

**Original Qwen3-Reranker:**
- Uses logits of "no" and "yes" tokens for scoring
- Requires computing logits for entire vocabulary (151,669 tokens)
- More computationally intensive

**Qwen3-Reranker-seq-cls:**
- Direct sequence classification output
- Single classification head
- More efficient (no full vocabulary computation)
- Compatible with standard cross-encoder frameworks

### 5.3 Usage Examples

**With Sentence Transformers (seq-cls variant):**
```python
from sentence_transformers import CrossEncoder

# Load model
model = CrossEncoder("tomaarsen/Qwen3-Reranker-0.6B-seq-cls")

# Define query-document pairs
pairs = [
    ["What is machine learning?", "Machine learning is a subset of AI..."],
    ["What is machine learning?", "The weather today is sunny..."],
    ["What is machine learning?", "ML algorithms learn from data..."],
]

# Get scores
scores = model.predict(pairs)
print(scores)  # [0.95, 0.02, 0.89]

# Rank documents
query = "What is machine learning?"
documents = [
    "Machine learning is a subset of AI...",
    "The weather today is sunny...",
    "ML algorithms learn from data..."
]

# Score all pairs
scores = model.predict([[query, doc] for doc in documents])

# Get ranked indices
ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

for i in ranked_indices:
    print(f"Score: {scores[i]:.4f} - {documents[i][:50]}...")
```

**With vLLM (original variant):**
```python
from vllm import LLM

# Initialize model
llm = LLM(
    model="Qwen/Qwen3-Reranker-0.6B",
    task="score",
    max_model_len=32768
)

# Prepare query-document pairs
query = "What is machine learning?"
documents = [
    "Machine learning is a subset of AI...",
    "The weather today is sunny...",
    "ML algorithms learn from data..."
]

# Score pairs
outputs = llm.score(query, documents)

for output in outputs:
    print(f"Score: {output.score:.4f}")
```

### 5.4 Deployment with TEI

**Docker Deployment:**
```bash
# Deploy Qwen3-Reranker with TEI
docker run --gpus all -p 8081:80 \
  -v $PWD/data:/data \
  --pull always \
  ghcr.io/huggingface/text-embeddings-inference:1.8 \
  --model-id Qwen/Qwen3-Reranker-0.6B \
  --max-batch-tokens 8192 \
  --max-client-batch-size 16
```

**Note**: Use the seq-cls variant if TEI requires sequence classification models:
```bash
docker run --gpus all -p 8081:80 \
  -v $PWD/data:/data \
  --pull always \
  ghcr.io/huggingface/text-embeddings-inference:1.8 \
  --model-id tomaarsen/Qwen3-Reranker-0.6B-seq-cls
```

**Verification:**
```bash
# Test reranker endpoint
curl http://localhost:8081/rerank \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "What is machine learning?",
    "texts": [
      "Machine learning is a subset of AI",
      "The weather is sunny today"
    ],
    "raw_scores": false
  }'
```

### 5.5 Performance Characteristics

**Computational Requirements:**
- 0.6B model: ~1.5GB GPU memory (FP16)
- 4B model: ~8GB GPU memory (FP16)
- 8B model: ~16GB GPU memory (FP16)

**Throughput:**
- Depends on sequence length and batch size
- TEI provides dynamic batching for optimal utilization
- Typical: 100-500 pairs/second (0.6B on A100)

**Quality:**
- Inherits reasoning capabilities from Qwen3 foundation model
- Strong multilingual performance
- Excellent long-context understanding

## 6. Complete Query Pipeline

### 6.1 Pipeline Architecture

The complete RAG pipeline with embeddings and reranking follows this flow:

```
1. Query → Embedding Generation (TEI Embed)
2. Embedding → Vector Search (Qdrant/Vector DB)
3. Top-K Results → Reranking (TEI Rerank)
4. Top-N Reranked → Response Generation (LLM)
```

**Pipeline Diagram:**
```
┌─────────────┐
│    Query    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│  Query Embedding (TEI)  │
│  Qwen3-Embedding-0.6B   │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   Vector Search         │
│   (Similarity Top-K)    │
│   Retrieve 20+ docs     │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   Reranking (TEI)       │
│   Qwen3-Reranker-0.6B   │
│   Select Top-N          │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Response Synthesis     │
│  (LLM Generation)       │
└─────────────────────────┘
```

### 6.2 LlamaIndex Query Pipeline Implementation

**Complete Workflow Example:**
```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.postprocessor.tei_rerank import TEIRerank

# 1. Configure custom TEI embedding model
from custom_embeddings import TEIEmbedding  # From section 2.3

embed_model = TEIEmbedding(
    base_url="http://localhost:8080",
    model_name="Qwen3-Embedding-0.6B",
    embed_batch_size=32
)

Settings.embed_model = embed_model

# 2. Load and index documents
documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)

# 3. Create retriever (get more candidates for reranking)
retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=20  # Retrieve 20 candidates
)

# 4. Create reranker
reranker = TEIRerank(
    base_url="http://localhost:8081",
    top_n=5  # Keep top 5 after reranking
)

# 5. Create query engine
query_engine = RetrieverQueryEngine(
    retriever=retriever,
    node_postprocessors=[reranker]
)

# 6. Query
response = query_engine.query("What are the main concepts in machine learning?")
print(response)

# Access source nodes with scores
for node in response.source_nodes:
    print(f"Score: {node.score:.4f}")
    print(f"Text: {node.node.get_content()[:200]}...")
    print()
```

### 6.3 Advanced Query Pipeline with Custom Components

**Using Query Pipeline API:**
```python
from llama_index.core.query_pipeline import QueryPipeline, InputComponent
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.postprocessor.tei_rerank import TEIRerank

# Build explicit pipeline
pipeline = QueryPipeline()

# 1. Input
input_component = InputComponent()

# 2. Retriever
retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=20
)

# 3. Reranker
reranker = TEIRerank(
    base_url="http://localhost:8081",
    top_n=5
)

# 4. Response synthesizer
synthesizer = CompactAndRefine()

# Connect components
pipeline.add_modules({
    "input": input_component,
    "retriever": retriever,
    "reranker": reranker,
    "synthesizer": synthesizer
})

# Define links
pipeline.add_link("input", "retriever")
pipeline.add_link("retriever", "reranker")
pipeline.add_link("reranker", "synthesizer")
pipeline.add_link("input", "synthesizer")  # Pass query to synthesizer

# Run pipeline
response = pipeline.run(query="What is machine learning?")
print(response)
```

### 6.4 Multi-Stage Retrieval Strategy

**Hybrid Retrieval with Reranking:**
```python
from llama_index.core.retrievers import (
    VectorIndexRetriever,
    KeywordTableSimpleRetriever,
    QueryFusionRetriever
)
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.postprocessor.tei_rerank import TEIRerank

# Stage 1: Multiple retrieval strategies
vector_retriever = VectorIndexRetriever(
    index=vector_index,
    similarity_top_k=15
)

keyword_retriever = KeywordTableSimpleRetriever(
    index=keyword_index,
    similarity_top_k=15
)

# Fusion retriever (combines results)
fusion_retriever = QueryFusionRetriever(
    retrievers=[vector_retriever, keyword_retriever],
    similarity_top_k=20,
    num_queries=1  # Don't generate query variations
)

# Stage 2: Reranking
reranker = TEIRerank(
    base_url="http://localhost:8081",
    top_n=5
)

# Create query engine
query_engine = RetrieverQueryEngine(
    retriever=fusion_retriever,
    node_postprocessors=[reranker]
)

# Query
response = query_engine.query("Complex query requiring hybrid search")
```

### 6.5 Evaluation and Metrics

**Measuring Pipeline Performance:**
```python
from llama_index.core.evaluation import (
    RetrieverEvaluator,
    RetrievalEvalResult
)

# Create evaluator
retriever_evaluator = RetrieverEvaluator.from_metric_names(
    ["mrr", "hit_rate"],
    retriever=retriever
)

# Evaluate
eval_results = retriever_evaluator.evaluate_dataset(eval_dataset)

# Compare with/without reranking
query_engine_no_rerank = index.as_query_engine(similarity_top_k=5)
query_engine_with_rerank = index.as_query_engine(
    similarity_top_k=20,
    node_postprocessors=[reranker]
)

# Test both
for query in test_queries:
    response_baseline = query_engine_no_rerank.query(query)
    response_reranked = query_engine_with_rerank.query(query)

    print(f"Query: {query}")
    print(f"Baseline: {response_baseline}")
    print(f"Reranked: {response_reranked}")
    print()
```

## 7. Code Examples

### 7.1 Complete Production Setup

**File: `embeddings.py`**
```python
"""TEI Embedding integration for LlamaIndex."""
from typing import Any, List
import requests
import aiohttp
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.bridge.pydantic import PrivateAttr


class TEIEmbedding(BaseEmbedding):
    """HuggingFace Text Embeddings Inference (TEI) integration."""

    _base_url: str = PrivateAttr()
    _timeout: int = PrivateAttr()
    _truncate: bool = PrivateAttr()

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        model_name: str = "text-embeddings-inference",
        embed_batch_size: int = 32,
        timeout: int = 60,
        truncate: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize TEI embedding client.

        Args:
            base_url: TEI service endpoint URL
            model_name: Model name for tracking
            embed_batch_size: Batch size for encoding
            timeout: Request timeout in seconds
            truncate: Whether to truncate long texts
        """
        super().__init__(
            model_name=model_name,
            embed_batch_size=embed_batch_size,
            **kwargs
        )
        self._base_url = base_url.rstrip('/')
        self._timeout = timeout
        self._truncate = truncate

    @classmethod
    def class_name(cls) -> str:
        return "TEIEmbedding"

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from TEI service."""
        url = f"{self._base_url}/embed"
        headers = {"Content-Type": "application/json"}
        payload = {"inputs": texts, "truncate": self._truncate}

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=self._timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"TEI embedding request failed: {str(e)}")

    async def _aembed_texts(self, texts: List[str]) -> List[List[float]]:
        """Async get embeddings from TEI service."""
        url = f"{self._base_url}/embed"
        headers = {"Content-Type": "application/json"}
        payload = {"inputs": texts, "truncate": self._truncate}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            raise RuntimeError(f"TEI embedding request failed: {str(e)}")

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._embed_texts([query])[0]

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._embed_texts([text])[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._embed_texts(texts)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        embeddings = await self._aembed_texts([query])
        return embeddings[0]

    async def _aget_text_embedding(self, text: str) -> List[float]:
        embeddings = await self._aembed_texts([text])
        return embeddings[0]
```

**File: `reranker.py`**
```python
"""TEI Reranker integration for LlamaIndex."""
from typing import List, Optional
import requests
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle


class TEIReranker(BaseNodePostprocessor):
    """HuggingFace TEI Reranker postprocessor."""

    base_url: str
    top_n: int = 5
    timeout: int = 60
    raw_scores: bool = False

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        top_n: int = 5,
        timeout: int = 60,
        raw_scores: bool = False,
        **kwargs
    ):
        """Initialize TEI reranker.

        Args:
            base_url: TEI reranker service URL
            top_n: Number of top results to return
            timeout: Request timeout in seconds
            raw_scores: Return raw logits vs normalized scores
        """
        super().__init__(
            base_url=base_url,
            top_n=top_n,
            timeout=timeout,
            raw_scores=raw_scores,
            **kwargs
        )

    @classmethod
    def class_name(cls) -> str:
        return "TEIReranker"

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Rerank nodes based on query relevance."""
        if not query_bundle or not nodes:
            return nodes

        # Extract texts
        texts = [node.node.get_content() for node in nodes]

        # Call TEI rerank API
        url = f"{self.base_url}/rerank"
        headers = {"Content-Type": "application/json"}
        payload = {
            "query": query_bundle.query_str,
            "texts": texts,
            "raw_scores": self.raw_scores
        }

        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()
            results = response.json()

            # Sort by score
            results = sorted(results, key=lambda x: x['score'], reverse=True)

            # Create reranked nodes
            reranked_nodes = []
            for result in results[:self.top_n]:
                idx = result['index']
                node = nodes[idx]
                node.score = result['score']
                reranked_nodes.append(node)

            return reranked_nodes

        except requests.exceptions.RequestException as e:
            print(f"Reranking failed: {e}, falling back to original order")
            return nodes[:self.top_n]
```

**File: `rag_pipeline.py`**
```python
"""Complete RAG pipeline with TEI embeddings and reranking."""
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    StorageContext
)
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from embeddings import TEIEmbedding
from reranker import TEIReranker


class RAGPipeline:
    """Production RAG pipeline with TEI."""

    def __init__(
        self,
        embed_url: str = "http://localhost:8080",
        rerank_url: str = "http://localhost:8081",
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "documents",
        similarity_top_k: int = 20,
        rerank_top_n: int = 5
    ):
        """Initialize RAG pipeline.

        Args:
            embed_url: TEI embedding service URL
            rerank_url: TEI reranker service URL
            qdrant_url: Qdrant vector store URL
            collection_name: Qdrant collection name
            similarity_top_k: Number of candidates to retrieve
            rerank_top_n: Number of final results after reranking
        """
        # 1. Configure embedding model
        self.embed_model = TEIEmbedding(
            base_url=embed_url,
            model_name="Qwen3-Embedding-0.6B",
            embed_batch_size=32
        )
        Settings.embed_model = self.embed_model

        # 2. Configure vector store
        self.qdrant_client = QdrantClient(url=qdrant_url)
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=collection_name
        )
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )

        # 3. Configure reranker
        self.reranker = TEIReranker(
            base_url=rerank_url,
            top_n=rerank_top_n
        )

        # Store config
        self.similarity_top_k = similarity_top_k
        self.collection_name = collection_name
        self.index = None

    def index_documents(self, documents_path: str) -> None:
        """Index documents into vector store."""
        # Load documents
        documents = SimpleDirectoryReader(documents_path).load_data()

        # Create index
        self.index = VectorStoreIndex.from_documents(
            documents,
            storage_context=self.storage_context
        )

        print(f"Indexed {len(documents)} documents")

    def load_index(self) -> None:
        """Load existing index from vector store."""
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            storage_context=self.storage_context
        )
        print("Loaded existing index")

    def create_query_engine(self):
        """Create query engine with retrieval and reranking."""
        if not self.index:
            raise ValueError("Index not loaded. Call index_documents() or load_index()")

        # Create retriever
        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=self.similarity_top_k
        )

        # Create query engine
        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            node_postprocessors=[self.reranker]
        )

        return query_engine

    def query(self, question: str, verbose: bool = False):
        """Query the RAG pipeline."""
        query_engine = self.create_query_engine()
        response = query_engine.query(question)

        if verbose:
            print(f"\nQuery: {question}")
            print(f"\nResponse: {response}\n")
            print("Source Nodes:")
            for i, node in enumerate(response.source_nodes):
                print(f"\n{i+1}. Score: {node.score:.4f}")
                print(f"   Text: {node.node.get_content()[:200]}...")

        return response


# Usage
if __name__ == "__main__":
    # Initialize pipeline
    pipeline = RAGPipeline(
        embed_url="http://localhost:8080",
        rerank_url="http://localhost:8081",
        qdrant_url="http://localhost:6333",
        collection_name="my_documents",
        similarity_top_k=20,
        rerank_top_n=5
    )

    # Index documents (first time)
    # pipeline.index_documents("./data")

    # Or load existing index
    pipeline.load_index()

    # Query
    response = pipeline.query(
        "What are the main concepts in machine learning?",
        verbose=True
    )
```

### 7.2 Docker Compose Setup

**File: `docker-compose.yml`**
```yaml
version: '3.8'

services:
  # TEI Embedding Service
  tei-embedding:
    image: ghcr.io/huggingface/text-embeddings-inference:1.8
    container_name: tei-embedding
    command:
      - --model-id
      - Qwen/Qwen3-Embedding-0.6B
      - --max-batch-tokens
      - "16384"
      - --max-client-batch-size
      - "32"
    ports:
      - "8080:80"
    volumes:
      - ./data/models/embedding:/data
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # TEI Reranker Service
  tei-reranker:
    image: ghcr.io/huggingface/text-embeddings-inference:1.8
    container_name: tei-reranker
    command:
      - --model-id
      - tomaarsen/Qwen3-Reranker-0.6B-seq-cls
      - --max-batch-tokens
      - "8192"
      - --max-client-batch-size
      - "16"
    ports:
      - "8081:80"
    volumes:
      - ./data/models/reranker:/data
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Qdrant Vector Store
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  models-embedding:
  models-reranker:
  qdrant-storage:
```

**Start Services:**
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f tei-embedding
docker-compose logs -f tei-reranker

# Test embedding service
curl http://localhost:8080/health
curl http://localhost:8080/embed \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"inputs": "Test embedding"}'

# Test reranker service
curl http://localhost:8081/health
curl http://localhost:8081/rerank \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "test query",
    "texts": ["relevant text", "irrelevant text"]
  }'
```

### 7.3 Testing and Validation

**File: `test_pipeline.py`**
```python
"""Tests for RAG pipeline."""
import pytest
from rag_pipeline import RAGPipeline


def test_embedding_service():
    """Test TEI embedding service connectivity."""
    from embeddings import TEIEmbedding

    embed_model = TEIEmbedding(base_url="http://localhost:8080")

    # Test single embedding
    text = "Test document"
    embedding = embed_model.get_text_embedding(text)

    assert len(embedding) == 1024  # Qwen3-0.6B dimension
    assert isinstance(embedding, list)
    assert all(isinstance(x, float) for x in embedding)


def test_reranker_service():
    """Test TEI reranker service connectivity."""
    from reranker import TEIReranker
    from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle

    reranker = TEIReranker(base_url="http://localhost:8081", top_n=2)

    # Create mock nodes
    nodes = [
        NodeWithScore(node=TextNode(text="Machine learning is AI"), score=0.5),
        NodeWithScore(node=TextNode(text="The weather is sunny"), score=0.5),
        NodeWithScore(node=TextNode(text="ML algorithms learn"), score=0.5),
    ]

    # Rerank
    query = QueryBundle(query_str="What is machine learning?")
    reranked = reranker._postprocess_nodes(nodes, query)

    assert len(reranked) == 2
    assert reranked[0].score > reranked[1].score


def test_end_to_end_pipeline():
    """Test complete RAG pipeline."""
    pipeline = RAGPipeline(
        embed_url="http://localhost:8080",
        rerank_url="http://localhost:8081",
        similarity_top_k=10,
        rerank_top_n=3
    )

    # Load index
    pipeline.load_index()

    # Query
    response = pipeline.query("What is machine learning?")

    assert response is not None
    assert len(response.source_nodes) <= 3  # rerank_top_n
    assert all(hasattr(node, 'score') for node in response.source_nodes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## Summary

This document provides comprehensive integration patterns for HuggingFace TEI with LlamaIndex:

1. **TEI API**: HTTP endpoints for embeddings and reranking with batch support
2. **Custom Embeddings**: BaseEmbedding implementation for TEI integration
3. **Qwen3 Embedding**: 1024-dim vectors, 32K context, 100+ languages
4. **TEI Reranker**: Cross-encoder reranking for improved retrieval quality
5. **Qwen3 Reranker**: 0.6B-8B variants with seq-cls optimization
6. **Complete Pipeline**: End-to-end RAG with vector search and reranking
7. **Production Code**: Docker deployment, testing, and monitoring

**Key Takeaways:**
- Use TEI for high-performance self-hosted inference
- Retrieve 20+ candidates, rerank to top 5 for optimal quality
- Qwen3 models provide excellent multilingual and long-context support
- Custom implementations allow full control over the pipeline
- Production setup includes Docker Compose for easy deployment
