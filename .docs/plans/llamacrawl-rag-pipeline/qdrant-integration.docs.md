# Qdrant Vector Database Integration Guide

## Overview

This document provides comprehensive guidance on integrating Qdrant vector database into a multi-source RAG pipeline. Qdrant is a high-performance vector search engine designed for similarity search and AI applications.

**Key Resources:**
- Official Documentation: https://qdrant.tech/documentation/
- Python Client: https://python-client.qdrant.tech/
- GitHub Repository: https://github.com/qdrant/qdrant-client
- LlamaIndex Integration: https://qdrant.tech/documentation/frameworks/llama-index/

---

## 1. Python Client Usage

### 1.1 Connection Patterns

#### Local In-Memory Mode
Best for development, testing, and lightweight experiments:

```python
from qdrant_client import QdrantClient

# In-memory (no persistence)
client = QdrantClient(":memory:")

# Persistent local storage
client = QdrantClient(path="/path/to/db")
```

#### Remote Server Connection

```python
# Using host and port
client = QdrantClient(host="localhost", port=6333)

# Using URL
client = QdrantClient(url="http://localhost:6333")

# With gRPC (typically faster for uploads)
client = QdrantClient(
    host="localhost",
    grpc_port=6334,
    prefer_grpc=True
)
```

#### Cloud/Production Connection

```python
client = QdrantClient(
    url="https://your-cluster.qdrant.io",
    api_key="your-api-key"
)
```

### 1.2 Async Client Pattern

Starting from version 1.6.1, all methods are available in async:

```python
import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

async def setup_collection():
    client = AsyncQdrantClient(url="http://localhost:6333")

    # Create collection
    await client.create_collection(
        collection_name="documents",
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

    # Upsert points
    await client.upsert(
        collection_name="documents",
        points=[...]
    )

    # Search
    results = await client.query_points(
        collection_name="documents",
        query=[0.1, 0.2, ...],
        limit=10
    )

    return results

# Run async function
results = asyncio.run(setup_collection())
```

**When to use async:**
- Applications serving multiple concurrent users
- IO-bound operations that benefit from non-blocking calls
- Avoid for simple scripts that run once per day

### 1.3 Collection Management

#### Creating Collections

```python
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")

# Basic collection with single vector
client.create_collection(
    collection_name="documents",
    vectors_config=models.VectorParams(
        size=384,  # Embedding dimension
        distance=models.Distance.COSINE
    )
)

# Collection with multiple named vectors (multi-source RAG)
client.create_collection(
    collection_name="multi_source_docs",
    vectors_config={
        "text_embedding": models.VectorParams(
            size=384,
            distance=models.Distance.COSINE
        ),
        "image_embedding": models.VectorParams(
            size=512,
            distance=models.Distance.DOT
        ),
    }
)

# With advanced configuration
client.create_collection(
    collection_name="optimized_docs",
    vectors_config=models.VectorParams(
        size=1024,
        distance=models.Distance.COSINE,
        datatype=models.Datatype.UINT8  # For quantization
    ),
    shard_number=2,  # Distributed sharding
    replication_factor=2,  # High availability
    on_disk_payload=True  # Store payload on disk to save RAM
)
```

#### Distance Metrics

Choose based on your embedding model:

- **COSINE**: Most common, works with normalized vectors (0-1 range)
- **DOT**: For normalized vectors where larger dot product = more similar
- **EUCLIDEAN**: For absolute distance measurements

```python
# Distance metric comparison
models.Distance.COSINE     # Cosine similarity (most common)
models.Distance.DOT        # Dot product
models.Distance.EUCLIDEAN  # Euclidean distance
```

### 1.4 Indexing Operations

#### Batch Insert with PointStruct

```python
from qdrant_client.models import PointStruct
import uuid

# Prepare points
points = [
    PointStruct(
        id=str(uuid.uuid4()),
        vector=[0.05, 0.61, 0.76, 0.74],
        payload={
            "source": "github",
            "url": "https://github.com/repo/file.py",
            "timestamp": "2025-01-15T10:30:00Z",
            "metadata": {
                "language": "python",
                "stars": 1500
            }
        }
    ),
    PointStruct(
        id=str(uuid.uuid4()),
        vector=[0.19, 0.81, 0.75, 0.11],
        payload={
            "source": "documentation",
            "url": "https://docs.example.com/api",
            "timestamp": "2025-01-15T11:00:00Z"
        }
    )
]

# Upsert points
operation_info = client.upsert(
    collection_name="documents",
    wait=True,  # Wait for operation to complete
    points=points
)
```

#### Batch Insert with Batch Model

```python
from qdrant_client.models import Batch

client.upsert(
    collection_name="documents",
    points=Batch(
        ids=[1, 2, 3, 4, 5],
        vectors=[
            [0.9, 0.1, 0.1, 0.5],
            [0.1, 0.9, 0.1, 0.6],
            [0.1, 0.1, 0.9, 0.7],
            [0.8, 0.2, 0.3, 0.4],
            [0.3, 0.7, 0.4, 0.8]
        ],
        payloads=[
            {"category": "docs", "priority": "high"},
            {"category": "code", "priority": "medium"},
            {"category": "docs", "priority": "low"},
            {"category": "api", "priority": "high"},
            {"category": "tutorial", "priority": "medium"}
        ]
    )
)
```

#### Automatic Batch Upload (Recommended for Large Datasets)

```python
# For large datasets, use upload_points with automatic batching
from qdrant_client.models import PointStruct

def generate_points():
    """Generator for large datasets"""
    for i in range(100000):
        yield PointStruct(
            id=i,
            vector=generate_embedding(i),  # Your embedding function
            payload={"doc_id": i, "source": "crawler"}
        )

# Automatically handles batching, parallelization, and retries
client.upload_points(
    collection_name="documents",
    points=generate_points(),
    parallel=4,  # Number of parallel upload threads
    batch_size=100  # Points per batch
)
```

#### Named Vector Upsert (Multi-source RAG)

```python
from qdrant_client.models import PointStruct, NamedVector

points = [
    PointStruct(
        id=1,
        vector={
            "text_embedding": [0.1, 0.2, 0.3, 0.4],
            "image_embedding": [0.5, 0.6, 0.7, 0.8, 0.9]
        },
        payload={
            "content": "Document with text and images",
            "source": "web_crawler"
        }
    )
]

client.upsert(
    collection_name="multi_source_docs",
    points=points
)
```

---

## 2. Metadata Filtering

### 2.1 Filter Types and Syntax

#### Basic Match Filters

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Exact match
filter_exact = Filter(
    must=[
        FieldCondition(
            key="source",
            match=MatchValue(value="github")
        )
    ]
)

# Multiple conditions (AND logic)
filter_multi = Filter(
    must=[
        FieldCondition(key="source", match=MatchValue(value="github")),
        FieldCondition(key="language", match=MatchValue(value="python"))
    ]
)
```

#### Range Filters

```python
from qdrant_client.models import Range

# Numeric range
filter_range = Filter(
    must=[
        FieldCondition(
            key="stars",
            range=Range(gte=100, lte=5000)  # 100 <= stars <= 5000
        )
    ]
)

# Date range (stored as timestamps)
filter_dates = Filter(
    must=[
        FieldCondition(
            key="created_at",
            range=Range(
                gte="2025-01-01T00:00:00Z",
                lte="2025-12-31T23:59:59Z"
            )
        )
    ]
)
```

#### Complex Boolean Logic

```python
# Combining AND, OR, NOT
complex_filter = Filter(
    must=[
        # Required: must be documentation
        FieldCondition(key="type", match=MatchValue(value="documentation"))
    ],
    should=[
        # At least one should match (OR logic)
        FieldCondition(key="language", match=MatchValue(value="python")),
        FieldCondition(key="language", match=MatchValue(value="javascript"))
    ],
    must_not=[
        # Exclude these
        FieldCondition(key="status", match=MatchValue(value="deprecated"))
    ]
)
```

#### Array/List Filtering

```python
# Match any value in array
filter_array = Filter(
    must=[
        FieldCondition(
            key="tags",
            match=MatchValue(value="machine-learning")
        ),
        FieldCondition(
            key="tags",
            match=MatchValue(value="python")
        )
    ]
)
```

#### Nested Object Filtering

```python
# Use dot notation for nested fields
filter_nested = Filter(
    must=[
        FieldCondition(
            key="metadata.repository.owner",
            match=MatchValue(value="llamaindex")
        ),
        FieldCondition(
            key="metadata.stars",
            range=Range(gte=1000)
        )
    ]
)
```

### 2.2 Filtered Search Examples

```python
# Basic filtered search
results = client.query_points(
    collection_name="documents",
    query=[0.2, 0.1, 0.9, 0.7],  # Query vector
    query_filter=Filter(
        must=[
            FieldCondition(key="source", match=MatchValue(value="github")),
            FieldCondition(key="language", match=MatchValue(value="python"))
        ]
    ),
    limit=10,
    with_payload=True,
    with_vectors=False
)

# Multi-source RAG with date filtering
results = client.query_points(
    collection_name="multi_source_docs",
    query=[0.1] * 384,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="timestamp",
                range=Range(gte="2025-01-01T00:00:00Z")
            )
        ],
        should=[
            FieldCondition(key="source", match=MatchValue(value="github")),
            FieldCondition(key="source", match=MatchValue(value="documentation")),
            FieldCondition(key="source", match=MatchValue(value="stackoverflow"))
        ]
    ),
    limit=20
)
```

### 2.3 Indexing for Efficient Filtering

```python
# Create payload index for frequently filtered fields
client.create_payload_index(
    collection_name="documents",
    field_name="source",
    field_schema="keyword"  # For exact matching
)

client.create_payload_index(
    collection_name="documents",
    field_name="timestamp",
    field_schema="datetime"  # For date/time filtering
)

client.create_payload_index(
    collection_name="documents",
    field_name="stars",
    field_schema="integer"  # For numeric range queries
)

# Multi-tenant index with optimizations
client.create_payload_index(
    collection_name="documents",
    field_name="user_id",
    field_schema="keyword",
    is_tenant=True  # Optimize for multi-tenancy
)

# On-disk index to save RAM
client.create_payload_index(
    collection_name="documents",
    field_name="metadata",
    field_schema="keyword",
    on_disk=True
)
```

**Best Practices:**
- Index fields that constrain results the most (e.g., unique IDs, tenant IDs)
- High-cardinality fields benefit most from indexing
- For multi-tenant apps, use `is_tenant=True` for user/tenant ID fields
- Use `on_disk=True` for large indexes when RAM is limited
- Don't index every field - only those used in filters

---

## 3. Performance Optimization

### 3.1 HNSW Parameters

HNSW (Hierarchical Navigable Small World) is the graph-based index used for vector search.

#### Key Parameters

```python
from qdrant_client.models import HnswConfigDiff

# Default values (balanced)
# m = 16 (edges per node)
# ef_construct = 100 (neighbors during index building)

# High precision configuration
client.create_collection(
    collection_name="high_precision_docs",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    hnsw_config=HnswConfigDiff(
        m=64,  # More edges = more accurate but uses more memory
        ef_construct=512,  # More neighbors = better quality but slower indexing
        full_scan_threshold=10000,  # Use full scan for small collections
    )
)

# Speed-optimized configuration
client.create_collection(
    collection_name="fast_docs",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    hnsw_config=HnswConfigDiff(
        m=8,  # Fewer edges = faster but less accurate
        ef_construct=64,  # Faster indexing
    )
)
```

#### Search-Time HNSW Parameters

```python
# Adjust search precision at query time
results = client.query_points(
    collection_name="documents",
    query=[0.1] * 384,
    search_params=models.SearchParams(
        hnsw_ef=256,  # Higher = more accurate but slower
        exact=False   # Set True for brute-force exact search
    ),
    limit=10
)
```

**Tuning Guidelines:**
- **m**: Default 16. Increase to 32-64 for better accuracy, decrease to 8 for faster indexing
- **ef_construct**: Default 100. Increase to 256-512 for better quality
- **hnsw_ef** (search): Increase for better recall, decrease for faster search

### 3.2 Quantization Options

Quantization reduces memory usage and speeds up search by compressing vectors.

#### Scalar Quantization (Recommended)

```python
from qdrant_client.models import ScalarQuantization, ScalarType, QuantizationSearchParams

# Enable scalar quantization
client.create_collection(
    collection_name="quantized_docs",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    quantization_config=ScalarQuantization(
        scalar=ScalarType.INT8,  # Convert float32 to int8
        quantile=0.99,  # Outlier handling
        always_ram=True  # Keep quantized vectors in RAM for speed
    )
)

# Search with rescoring for accuracy
results = client.query_points(
    collection_name="quantized_docs",
    query=[0.1] * 384,
    search_params=QuantizationSearchParams(
        quantization=models.QuantizationSearchParams(
            ignore=False,  # Use quantization
            rescore=True,  # Rescore with original vectors
            oversampling=2.0  # Fetch 2x results for rescoring
        )
    ),
    limit=10
)
```

**Benefits:**
- 4x memory reduction (float32 → int8)
- Faster search using SIMD CPU instructions
- Minimal accuracy loss with rescoring

#### Binary Quantization (Maximum Speed)

```python
from qdrant_client.models import BinaryQuantization

# Enable binary quantization (1-bit per dimension)
client.create_collection(
    collection_name="binary_docs",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    quantization_config=BinaryQuantization(
        binary=models.BinaryQuantizationConfig(
            always_ram=True
        )
    )
)
```

**Benefits:**
- Up to 40x speedup
- 32x memory reduction
- **Requirements**: High-dimensional vectors (768+), centered distribution

#### Multi-bit Quantization

```python
# Available in Qdrant 1.15+
# 1.5-bit or 2-bit for better accuracy than binary
from qdrant_client.models import ProductQuantization

client.create_collection(
    collection_name="multibit_docs",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    quantization_config=ProductQuantization(
        product=models.ProductQuantizationConfig(
            compression=models.CompressionRatio.X16,  # 16x compression
            always_ram=True
        )
    )
)
```

### 3.3 Batch Operations

```python
# Parallel batch uploads
client.upload_points(
    collection_name="documents",
    points=point_generator(),
    parallel=8,  # Number of parallel workers
    batch_size=100,  # Points per batch
    max_retries=3  # Retry failed batches
)

# Batch search (multiple queries at once)
search_queries = [
    models.SearchRequest(
        vector=[0.1] * 384,
        filter=Filter(must=[FieldCondition(key="source", match=MatchValue(value="github"))]),
        limit=10,
        with_payload=True
    ),
    models.SearchRequest(
        vector=[0.2] * 384,
        filter=Filter(must=[FieldCondition(key="source", match=MatchValue(value="docs"))]),
        limit=10,
        with_payload=True
    )
]

batch_results = client.search_batch(
    collection_name="documents",
    requests=search_queries
)
```

### 3.4 Memory Optimization Strategies

#### Store Vectors on Disk

```python
from qdrant_client.models import OptimizersConfigDiff

# Store vectors on disk, keep index in RAM
client.create_collection(
    collection_name="disk_docs",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    optimizers_config=OptimizersConfigDiff(
        memmap_threshold=20000  # Store on disk after 20k vectors
    ),
    on_disk_payload=True  # Store payload on disk
)
```

#### Configuration Comparison

| Configuration | Memory | Speed | Accuracy | Use Case |
|---------------|--------|-------|----------|----------|
| Default | High | Fast | High | Small datasets, high RAM |
| Scalar Quantization | Medium | Fast | High | Balanced, most use cases |
| Binary Quantization | Very Low | Very Fast | Medium | Large scale, high-dim vectors |
| On-Disk Vectors | Very Low | Medium | High | Limited RAM, large datasets |
| Quantization + Disk | Lowest | Medium | Medium-High | Maximum scale, cost optimization |

---

## 4. Schema Design for Multi-Source RAG

### 4.1 Point Structure

Each point in Qdrant consists of:
- **ID**: Unique identifier (string or integer)
- **Vector(s)**: One or more embeddings
- **Payload**: JSON metadata

#### Single-Vector Schema

```python
from qdrant_client.models import PointStruct

point = PointStruct(
    id="doc_123",
    vector=[0.1, 0.2, 0.3, ...],  # 384-dim embedding
    payload={
        # Source identification
        "source_type": "github",
        "source_url": "https://github.com/org/repo/blob/main/file.py",

        # Content metadata
        "title": "Example Python Script",
        "content_preview": "First 200 chars...",
        "language": "python",

        # Temporal metadata
        "created_at": "2025-01-15T10:30:00Z",
        "updated_at": "2025-01-20T14:45:00Z",
        "indexed_at": "2025-01-21T09:00:00Z",

        # Categorization
        "tags": ["machine-learning", "data-processing"],
        "category": "code",

        # Quality signals
        "stars": 1500,
        "views": 5000,
        "priority": "high",

        # Nested metadata
        "repository": {
            "owner": "organization",
            "name": "project",
            "full_name": "organization/project"
        }
    }
)
```

#### Multi-Vector Schema (Named Vectors)

For different embedding types per document:

```python
# Collection with multiple vector types
client.create_collection(
    collection_name="multi_modal_docs",
    vectors_config={
        # Text embeddings (e.g., BERT, sentence-transformers)
        "text_dense": models.VectorParams(
            size=384,
            distance=models.Distance.COSINE
        ),
        # Sparse embeddings (e.g., SPLADE for keyword matching)
        "text_sparse": models.SparseVectorParams(),
        # Code embeddings (e.g., CodeBERT)
        "code": models.VectorParams(
            size=768,
            distance=models.Distance.COSINE
        ),
        # Image embeddings (e.g., CLIP)
        "image": models.VectorParams(
            size=512,
            distance=models.Distance.DOT
        )
    }
)

# Point with multiple embeddings
multi_vector_point = PointStruct(
    id="doc_456",
    vector={
        "text_dense": [0.1] * 384,
        "text_sparse": models.SparseVector(
            indices=[10, 50, 123, 456],
            values=[0.8, 0.6, 0.7, 0.9]
        ),
        "code": [0.2] * 768,
        "image": [0.3] * 512
    },
    payload={
        "source_type": "documentation",
        "title": "API Reference with Code Examples",
        "has_code": True,
        "has_images": True
    }
)
```

### 4.2 Multi-Source RAG Schema Pattern

#### Recommended Payload Structure

```python
{
    # === Source Identification ===
    "source_type": "github|documentation|stackoverflow|wiki|web",
    "source_id": "unique_id_from_source",
    "source_url": "full_url",

    # === Content ===
    "title": "Document title",
    "content": "Full text content or chunk",
    "content_hash": "sha256_hash",  # For deduplication
    "chunk_index": 0,  # If document is chunked
    "total_chunks": 5,
    "parent_doc_id": "doc_123",  # Link to parent document

    # === Temporal ===
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-20T14:45:00Z",
    "indexed_at": "2025-01-21T09:00:00Z",
    "crawled_at": "2025-01-21T08:00:00Z",

    # === Categorization ===
    "category": "code|docs|tutorial|api|discussion",
    "tags": ["python", "api", "rest"],
    "language": "python",  # Programming language or natural language

    # === Quality Signals ===
    "quality_score": 0.85,
    "relevance_score": 0.92,
    "authority_score": 0.78,

    # === Source-Specific Metadata ===
    "github": {
        "repository": "org/repo",
        "stars": 1500,
        "forks": 200,
        "path": "src/main.py",
        "branch": "main"
    },
    "stackoverflow": {
        "question_id": 12345,
        "answer_id": 67890,
        "score": 150,
        "accepted": True,
        "view_count": 10000
    },
    "documentation": {
        "version": "2.0.1",
        "section": "API Reference",
        "depth": 2
    }
}
```

#### Multi-Tenant Schema

```python
{
    # Tenant isolation
    "tenant_id": "user_123",
    "organization_id": "org_456",
    "access_level": "private|shared|public",

    # Rest of the fields...
    "source_type": "...",
    # ...
}

# Create tenant index
client.create_payload_index(
    collection_name="multi_tenant_docs",
    field_name="tenant_id",
    field_schema="keyword",
    is_tenant=True  # Optimizes for tenant-based queries
)
```

### 4.3 Faceted Search Schema

Enable efficient aggregations and faceting:

```python
# Create indexes for faceted fields
client.create_payload_index(
    collection_name="documents",
    field_name="source_type",
    field_schema="keyword"
)

client.create_payload_index(
    collection_name="documents",
    field_name="category",
    field_schema="keyword"
)

client.create_payload_index(
    collection_name="documents",
    field_name="language",
    field_schema="keyword"
)

# Query facets (Qdrant 1.12+)
facet_result = client.facet(
    collection_name="documents",
    key="source_type",
    limit=10  # Top 10 facet values
)

# Returns: [
#   {"value": "github", "count": 5000},
#   {"value": "documentation", "count": 3000},
#   {"value": "stackoverflow", "count": 2000},
#   ...
# ]
```

---

## 5. Integration with LlamaIndex

### 5.1 Basic Integration

#### Installation

```bash
pip install llama-index llama-index-vector-stores-qdrant qdrant-client
```

#### Simple Setup

```python
import qdrant_client
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext

# Initialize Qdrant client
client = qdrant_client.QdrantClient(
    url="http://localhost:6333"
    # or location=":memory:" for testing
    # or url="https://xyz.qdrant.io", api_key="..." for cloud
)

# Create vector store
vector_store = QdrantVectorStore(
    client=client,
    collection_name="documents"
)

# Create storage context
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Load documents and create index
documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context
)

# Query
query_engine = index.as_query_engine()
response = query_engine.query("What is Qdrant?")
print(response)
```

### 5.2 Hybrid Search with LlamaIndex

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client
from llama_index.core import StorageContext

# Initialize with hybrid search enabled
client = qdrant_client.QdrantClient(location=":memory:")

vector_store = QdrantVectorStore(
    client=client,
    collection_name="hybrid_demo",
    enable_hybrid=True,  # Enable hybrid search
    batch_size=20,
    fastembed_sparse_model="prithvida/Splade_PP_en_v1"  # Sparse model
)

storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Load and index documents
documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context
)

# Query with hybrid search
query_engine = index.as_query_engine(
    similarity_top_k=10,
    vector_store_query_mode="hybrid"  # Use hybrid mode
)
response = query_engine.query("machine learning algorithms")
```

**Hybrid Search Benefits:**
- Dense vectors: Semantic similarity
- Sparse vectors: Keyword matching
- Combined: Better retrieval quality

### 5.3 Multi-Tenancy with LlamaIndex

```python
from llama_index.core import VectorStoreIndex, Document
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client

# Setup
client = qdrant_client.QdrantClient(location=":memory:")

# Function to create user-specific index
def create_user_index(user_id: str, documents: list):
    vector_store = QdrantVectorStore(
        client=client,
        collection_name="multi_tenant_docs"
    )

    # Add user_id to document metadata
    for doc in documents:
        doc.metadata["user_id"] = user_id
        doc.metadata["access_level"] = "private"

    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context
    )

    return index

# Create tenant index
client.create_payload_index(
    collection_name="multi_tenant_docs",
    field_name="user_id",
    field_schema="keyword",
    is_tenant=True
)

# Query for specific user
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

def query_user_documents(user_id: str, query_text: str):
    vector_store = QdrantVectorStore(
        client=client,
        collection_name="multi_tenant_docs"
    )

    index = VectorStoreIndex.from_vector_store(vector_store)

    # Create filter for user_id
    filters = MetadataFilters(
        filters=[
            ExactMatchFilter(key="user_id", value=user_id)
        ]
    )

    # Query with filter
    query_engine = index.as_query_engine(filters=filters)
    response = query_engine.query(query_text)

    return response
```

### 5.4 Metadata Filtering with LlamaIndex

```python
from llama_index.core.vector_stores import (
    MetadataFilters,
    MetadataFilter,
    FilterOperator
)

# Create filters
filters = MetadataFilters(
    filters=[
        MetadataFilter(
            key="source_type",
            value="github",
            operator=FilterOperator.EQ
        ),
        MetadataFilter(
            key="stars",
            value=1000,
            operator=FilterOperator.GTE
        ),
        MetadataFilter(
            key="created_at",
            value="2025-01-01T00:00:00Z",
            operator=FilterOperator.GTE
        )
    ]
)

# Query with filters
query_engine = index.as_query_engine(
    similarity_top_k=10,
    filters=filters
)

response = query_engine.query("Python machine learning libraries")
```

**Available Operators:**
- `EQ`: Equal
- `NE`: Not equal
- `GT`: Greater than
- `GTE`: Greater than or equal
- `LT`: Less than
- `LTE`: Less than or equal
- `IN`: In list
- `NIN`: Not in list

### 5.5 Advanced LlamaIndex Integration

#### Custom Retriever

```python
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core import get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine

# Create custom retriever with Qdrant-specific settings
retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=20,
    vector_store_kwargs={
        "qdrant_filters": {
            "must": [
                {"key": "source_type", "match": {"value": "documentation"}},
                {"key": "version", "match": {"value": "latest"}}
            ]
        }
    }
)

# Create query engine
response_synthesizer = get_response_synthesizer(response_mode="compact")
query_engine = RetrieverQueryEngine(
    retriever=retriever,
    response_synthesizer=response_synthesizer
)

response = query_engine.query("API authentication methods")
```

#### Re-ranking with Qdrant

```python
from llama_index.core.postprocessor import SimilarityPostprocessor

# Create query engine with re-ranking
query_engine = index.as_query_engine(
    similarity_top_k=50,  # Retrieve more candidates
    node_postprocessors=[
        SimilarityPostprocessor(similarity_cutoff=0.7)  # Filter by score
    ]
)
```

---

## 6. Code Examples

### 6.1 Complete Connection Setup

```python
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams
import os

class QdrantConnection:
    """Manages Qdrant client connection with different configurations"""

    @staticmethod
    def create_local_client(path: str = "./qdrant_db"):
        """Create local persistent client"""
        return QdrantClient(path=path)

    @staticmethod
    def create_memory_client():
        """Create in-memory client (testing)"""
        return QdrantClient(":memory:")

    @staticmethod
    def create_server_client(host: str = "localhost", port: int = 6333, prefer_grpc: bool = False):
        """Create client for Qdrant server"""
        if prefer_grpc:
            return QdrantClient(
                host=host,
                grpc_port=6334,
                prefer_grpc=True
            )
        return QdrantClient(host=host, port=port)

    @staticmethod
    def create_cloud_client(url: str, api_key: str):
        """Create client for Qdrant Cloud"""
        return QdrantClient(url=url, api_key=api_key)

    @staticmethod
    def create_client_from_env():
        """Create client from environment variables"""
        mode = os.getenv("QDRANT_MODE", "memory")

        if mode == "memory":
            return QdrantConnection.create_memory_client()
        elif mode == "local":
            path = os.getenv("QDRANT_PATH", "./qdrant_db")
            return QdrantConnection.create_local_client(path)
        elif mode == "server":
            host = os.getenv("QDRANT_HOST", "localhost")
            port = int(os.getenv("QDRANT_PORT", "6333"))
            return QdrantConnection.create_server_client(host, port)
        elif mode == "cloud":
            url = os.getenv("QDRANT_URL")
            api_key = os.getenv("QDRANT_API_KEY")
            return QdrantConnection.create_cloud_client(url, api_key)
        else:
            raise ValueError(f"Unknown QDRANT_MODE: {mode}")

# Usage
client = QdrantConnection.create_client_from_env()
```

### 6.2 Collection Setup with Best Practices

```python
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance, VectorParams, HnswConfigDiff,
    ScalarQuantization, ScalarType, OptimizersConfigDiff
)

def create_optimized_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int = 384,
    enable_quantization: bool = True,
    enable_disk_storage: bool = False,
    shard_number: int = 1
):
    """Create collection with optimization settings"""

    # Check if collection exists
    collections = client.get_collections().collections
    if any(c.name == collection_name for c in collections):
        print(f"Collection {collection_name} already exists")
        return

    # Vector configuration
    vectors_config = VectorParams(
        size=vector_size,
        distance=Distance.COSINE
    )

    # HNSW configuration (balanced)
    hnsw_config = HnswConfigDiff(
        m=16,
        ef_construct=100,
        full_scan_threshold=10000
    )

    # Quantization configuration
    quantization_config = None
    if enable_quantization:
        quantization_config = ScalarQuantization(
            scalar=ScalarType.INT8,
            quantile=0.99,
            always_ram=True
        )

    # Optimizer configuration
    optimizer_config = None
    if enable_disk_storage:
        optimizer_config = OptimizersConfigDiff(
            memmap_threshold=20000
        )

    # Create collection
    client.create_collection(
        collection_name=collection_name,
        vectors_config=vectors_config,
        hnsw_config=hnsw_config,
        quantization_config=quantization_config,
        optimizers_config=optimizer_config,
        shard_number=shard_number,
        on_disk_payload=enable_disk_storage
    )

    print(f"Created collection: {collection_name}")

    # Create common indexes
    create_common_indexes(client, collection_name)

def create_common_indexes(client: QdrantClient, collection_name: str):
    """Create indexes for common filter fields"""

    indexes = [
        ("source_type", "keyword"),
        ("category", "keyword"),
        ("language", "keyword"),
        ("created_at", "datetime"),
        ("stars", "integer"),
        ("tenant_id", "keyword")  # For multi-tenancy
    ]

    for field_name, field_schema in indexes:
        try:
            is_tenant = field_name == "tenant_id"
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_schema,
                is_tenant=is_tenant
            )
            print(f"Created index on {field_name}")
        except Exception as e:
            print(f"Failed to create index on {field_name}: {e}")

# Usage
client = QdrantClient(":memory:")
create_optimized_collection(
    client,
    collection_name="documents",
    vector_size=384,
    enable_quantization=True,
    enable_disk_storage=False
)
```

### 6.3 Batch Insert Pattern

```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Batch
from typing import List, Dict, Generator
import uuid
from datetime import datetime

class QdrantIndexer:
    """Handles batch insertion into Qdrant"""

    def __init__(self, client: QdrantClient, collection_name: str):
        self.client = client
        self.collection_name = collection_name

    def insert_documents(
        self,
        documents: List[Dict],
        embeddings: List[List[float]],
        batch_size: int = 100
    ):
        """Insert documents with batching"""

        if len(documents) != len(embeddings):
            raise ValueError("Documents and embeddings must have same length")

        points = [
            self._create_point(doc, emb)
            for doc, emb in zip(documents, embeddings)
        ]

        # Batch insert
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
                wait=True
            )
            print(f"Inserted batch {i // batch_size + 1}/{(len(points) + batch_size - 1) // batch_size}")

    def insert_documents_streaming(
        self,
        document_generator: Generator[tuple, None, None],
        parallel: int = 4,
        batch_size: int = 100
    ):
        """Insert documents using streaming upload"""

        def point_generator():
            for doc, embedding in document_generator:
                yield self._create_point(doc, embedding)

        self.client.upload_points(
            collection_name=self.collection_name,
            points=point_generator(),
            parallel=parallel,
            batch_size=batch_size
        )

    def _create_point(self, document: Dict, embedding: List[float]) -> PointStruct:
        """Create a point from document and embedding"""

        doc_id = document.get("id", str(uuid.uuid4()))

        # Ensure indexed_at timestamp
        if "indexed_at" not in document:
            document["indexed_at"] = datetime.utcnow().isoformat() + "Z"

        return PointStruct(
            id=doc_id,
            vector=embedding,
            payload=document
        )

# Usage example
def process_documents(documents: List[Dict], embed_func):
    """Process and index documents"""

    client = QdrantClient(":memory:")

    # Create collection
    client.create_collection(
        collection_name="documents",
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
    )

    # Index documents
    indexer = QdrantIndexer(client, "documents")

    # Generate embeddings
    embeddings = [embed_func(doc["content"]) for doc in documents]

    # Insert
    indexer.insert_documents(documents, embeddings, batch_size=100)

    print(f"Indexed {len(documents)} documents")
```

### 6.4 Query Patterns

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class QdrantSearcher:
    """Handles various search patterns in Qdrant"""

    def __init__(self, client: QdrantClient, collection_name: str):
        self.client = client
        self.collection_name = collection_name

    def search_basic(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> List[Dict]:
        """Basic vector search"""

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            }
            for hit in results.points
        ]

    def search_by_source(
        self,
        query_vector: List[float],
        source_types: List[str],
        limit: int = 10
    ) -> List[Dict]:
        """Search filtered by source type"""

        # Build filter for multiple source types
        filter_conditions = [
            FieldCondition(
                key="source_type",
                match=MatchValue(value=source)
            )
            for source in source_types
        ]

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=Filter(should=filter_conditions),  # OR logic
            limit=limit,
            with_payload=True
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "source": hit.payload.get("source_type"),
                "title": hit.payload.get("title"),
                "url": hit.payload.get("source_url")
            }
            for hit in results.points
        ]

    def search_recent(
        self,
        query_vector: List[float],
        days: int = 7,
        limit: int = 10
    ) -> List[Dict]:
        """Search recent documents"""

        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="created_at",
                        range=Range(gte=cutoff_date)
                    )
                ]
            ),
            limit=limit,
            with_payload=True
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "created_at": hit.payload.get("created_at"),
                "payload": hit.payload
            }
            for hit in results.points
        ]

    def search_multi_criteria(
        self,
        query_vector: List[float],
        source_type: Optional[str] = None,
        category: Optional[str] = None,
        min_quality: Optional[float] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Advanced multi-criteria search"""

        must_conditions = []

        if source_type:
            must_conditions.append(
                FieldCondition(key="source_type", match=MatchValue(value=source_type))
            )

        if category:
            must_conditions.append(
                FieldCondition(key="category", match=MatchValue(value=category))
            )

        if min_quality:
            must_conditions.append(
                FieldCondition(key="quality_score", range=Range(gte=min_quality))
            )

        if date_from or date_to:
            range_params = {}
            if date_from:
                range_params["gte"] = date_from
            if date_to:
                range_params["lte"] = date_to
            must_conditions.append(
                FieldCondition(key="created_at", range=Range(**range_params))
            )

        if tags:
            for tag in tags:
                must_conditions.append(
                    FieldCondition(key="tags", match=MatchValue(value=tag))
                )

        filter_obj = Filter(must=must_conditions) if must_conditions else None

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=filter_obj,
            limit=limit,
            with_payload=True
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            }
            for hit in results.points
        ]

    def search_tenant_isolated(
        self,
        query_vector: List[float],
        tenant_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Multi-tenant isolated search"""

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=tenant_id)
                    )
                ]
            ),
            limit=limit,
            with_payload=True
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            }
            for hit in results.points
        ]

# Usage
searcher = QdrantSearcher(client, "documents")

# Search recent documents from GitHub
results = searcher.search_multi_criteria(
    query_vector=[0.1] * 384,
    source_type="github",
    date_from="2025-01-01T00:00:00Z",
    min_quality=0.8,
    tags=["python", "machine-learning"],
    limit=20
)

for result in results:
    print(f"Score: {result['score']:.3f} - {result['payload']['title']}")
```

### 6.5 Complete Multi-Source RAG Example

```python
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, Range
from typing import List, Dict, Optional
import uuid
from datetime import datetime

class MultiSourceRAG:
    """Complete multi-source RAG system with Qdrant"""

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str = "multi_source_rag",
        vector_size: int = 384
    ):
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size

        self._setup_collection()

    def _setup_collection(self):
        """Initialize collection and indexes"""

        # Check if exists
        collections = self.client.get_collections().collections
        if any(c.name == self.collection_name for c in collections):
            print(f"Collection {self.collection_name} exists")
            return

        # Create collection with hybrid search support
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "text_dense": VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                ),
                "text_sparse": models.SparseVectorParams()
            },
            hnsw_config=models.HnswConfigDiff(
                m=16,
                ef_construct=100
            ),
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarType.INT8,
                quantile=0.99,
                always_ram=True
            )
        )

        # Create indexes
        self._create_indexes()

        print(f"Created collection: {self.collection_name}")

    def _create_indexes(self):
        """Create payload indexes for filtering"""

        indexes = [
            ("source_type", "keyword", False),
            ("category", "keyword", False),
            ("language", "keyword", False),
            ("created_at", "datetime", False),
            ("tenant_id", "keyword", True),  # Multi-tenant
        ]

        for field_name, field_schema, is_tenant in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                    is_tenant=is_tenant
                )
            except Exception as e:
                print(f"Index creation warning for {field_name}: {e}")

    def index_document(
        self,
        content: str,
        dense_embedding: List[float],
        sparse_embedding: Dict[str, List],  # {indices: [...], values: [...]}
        source_type: str,
        source_url: str,
        metadata: Dict,
        tenant_id: Optional[str] = None
    ) -> str:
        """Index a single document"""

        doc_id = str(uuid.uuid4())

        payload = {
            "content": content,
            "source_type": source_type,
            "source_url": source_url,
            "indexed_at": datetime.utcnow().isoformat() + "Z",
            **metadata
        }

        if tenant_id:
            payload["tenant_id"] = tenant_id

        point = PointStruct(
            id=doc_id,
            vector={
                "text_dense": dense_embedding,
                "text_sparse": models.SparseVector(
                    indices=sparse_embedding["indices"],
                    values=sparse_embedding["values"]
                )
            },
            payload=payload
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
            wait=True
        )

        return doc_id

    def search(
        self,
        query_dense: List[float],
        query_sparse: Optional[Dict] = None,
        source_types: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 10,
        use_hybrid: bool = True
    ) -> List[Dict]:
        """Search with optional filters"""

        # Build filter
        filter_conditions = []

        if source_types:
            filter_conditions.append(
                Filter(should=[
                    FieldCondition(key="source_type", match=MatchValue(value=st))
                    for st in source_types
                ])
            )

        if date_from:
            filter_conditions.append(
                FieldCondition(key="created_at", range=Range(gte=date_from))
            )

        if tenant_id:
            filter_conditions.append(
                FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
            )

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Perform search
        if use_hybrid and query_sparse:
            # Hybrid search
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=models.NamedVector(
                    name="text_dense",
                    vector=query_dense
                ),
                query_filter=query_filter,
                limit=limit,
                with_payload=True
            )
            # Note: Full hybrid search requires search_batch with multiple requests
        else:
            # Dense-only search
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_dense,
                using="text_dense",
                query_filter=query_filter,
                limit=limit,
                with_payload=True
            )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "content": hit.payload.get("content"),
                "source_type": hit.payload.get("source_type"),
                "source_url": hit.payload.get("source_url"),
                "metadata": hit.payload
            }
            for hit in results.points
        ]

# Usage Example
if __name__ == "__main__":
    # Initialize
    client = QdrantClient(":memory:")
    rag = MultiSourceRAG(client)

    # Index documents from different sources
    doc_id_1 = rag.index_document(
        content="Python machine learning with scikit-learn",
        dense_embedding=[0.1] * 384,
        sparse_embedding={"indices": [10, 20, 30], "values": [0.8, 0.6, 0.9]},
        source_type="github",
        source_url="https://github.com/example/ml",
        metadata={
            "language": "python",
            "stars": 1500,
            "category": "code"
        }
    )

    doc_id_2 = rag.index_document(
        content="Scikit-learn documentation for machine learning",
        dense_embedding=[0.15] * 384,
        sparse_embedding={"indices": [15, 25, 35], "values": [0.7, 0.8, 0.6]},
        source_type="documentation",
        source_url="https://scikit-learn.org/docs",
        metadata={
            "version": "1.3.0",
            "category": "docs"
        }
    )

    # Search
    results = rag.search(
        query_dense=[0.12] * 384,
        source_types=["github", "documentation"],
        limit=10
    )

    print(f"Found {len(results)} results:")
    for result in results:
        print(f"  - [{result['source_type']}] {result['content'][:50]}... (score: {result['score']:.3f})")
```

---

## Summary and Recommendations

### Key Takeaways

1. **Connection Patterns**: Start with in-memory for testing, use local/server for development, cloud for production
2. **Schema Design**: Use structured payloads with source_type, timestamps, and metadata for multi-source RAG
3. **Indexing**: Create payload indexes on frequently filtered fields (source_type, tenant_id, dates)
4. **Performance**: Enable scalar quantization for 4x memory reduction with minimal accuracy loss
5. **LlamaIndex**: Use QdrantVectorStore for seamless integration with hybrid search and metadata filtering
6. **Multi-tenancy**: Use `is_tenant=True` on tenant_id indexes for optimized isolation

### Recommended Architecture for LlamaCrawl RAG Pipeline

```python
# 1. Collection per data domain OR single collection with source_type filter
# 2. Hybrid search (dense + sparse) for best retrieval quality
# 3. Multi-tenant support with tenant_id filtering
# 4. Scalar quantization for production scale
# 5. Payload indexes on: source_type, category, created_at, tenant_id
# 6. Named vectors for different embedding types (text, code, image)
```

### Performance Tuning Quick Reference

| Metric | Goal | Configuration |
|--------|------|---------------|
| Memory | Minimize | Scalar quantization, on-disk storage |
| Speed | Maximize | Binary quantization, lower HNSW m |
| Accuracy | Maximize | Higher HNSW m/ef_construct, rescoring |
| Scale | Maximum | Quantization + sharding + disk storage |

### References

- Qdrant Documentation: https://qdrant.tech/documentation/
- Python Client Docs: https://python-client.qdrant.tech/
- LlamaIndex Integration: https://qdrant.tech/documentation/frameworks/llama-index/
- Optimization Guide: https://qdrant.tech/documentation/guides/optimize/
- Filtering Guide: https://qdrant.tech/documentation/concepts/filtering/
- Quantization Guide: https://qdrant.tech/documentation/guides/quantization/
- Hybrid Search: https://qdrant.tech/documentation/beginner-tutorials/hybrid-search-fastembed/

---

**Document Version**: 1.0
**Last Updated**: 2025-01-30
**Target**: LlamaCrawl RAG Pipeline Integration
