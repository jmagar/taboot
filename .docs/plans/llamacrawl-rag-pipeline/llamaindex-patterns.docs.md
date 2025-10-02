# LlamaIndex RAG Pipeline Patterns and Best Practices

## Overview

This document provides comprehensive patterns and best practices for building production-ready RAG (Retrieval-Augmented Generation) pipelines using LlamaIndex framework. It focuses on core architectural patterns, integration strategies, and concrete code examples applicable to the llamacrawl project.

**Key Documentation Resources:**
- Official LlamaIndex Docs: https://docs.llamaindex.ai/en/stable/
- Production RAG Guide: https://docs.llamaindex.ai/en/stable/optimizing/production_rag/
- High-Level Concepts: https://docs.llamaindex.ai/en/stable/getting_started/concepts/
- Building from Scratch: https://docs.llamaindex.ai/en/stable/examples/low_level/oss_ingestion_retrieval/

---

## 1. Core Architecture Patterns

### 1.1 Project Structure

LlamaIndex applications follow a modular architecture with these key components:

```
RAG Pipeline Architecture:
┌─────────────────────────────────────────────────────────────┐
│                     Data Sources                             │
│  (FireCrawl, Gmail, GitHub, PDFs, etc.)                     │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Ingestion Pipeline                              │
│  • Document Readers                                          │
│  • Transformations (Chunking, Metadata Extraction)          │
│  • Embeddings Generation                                     │
│  • Caching (Redis)                                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Storage Layer                                   │
│  • Vector Store (Qdrant)                                     │
│  • Graph Store (Neo4j)                                       │
│  • Document Store (Redis)                                    │
│  • Index Store                                               │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Query Engine                                    │
│  • Retrievers (Vector, Hybrid, Graph)                       │
│  • Rerankers                                                 │
│  • Response Synthesizers                                     │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   LLM Response                               │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Settings Configuration

**Modern Approach (v0.10.0+)**: Use the global Settings object instead of ServiceContext.

```python
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter

# Global configuration - applies to all modules
Settings.llm = OpenAI(model="gpt-4", temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)
Settings.num_output = 512
Settings.context_window = 3900
```

**Key Configuration Attributes:**
- `llm`: Language model for response generation
- `embed_model`: Embedding model for vector representations
- `node_parser`: Document chunking strategy
- `num_output`: Maximum tokens in response
- `context_window`: Maximum context size for LLM
- `chunk_size`: Size of document chunks
- `chunk_overlap`: Overlap between chunks

### 1.3 StorageContext Pattern

The StorageContext manages all storage backends:

```python
from llama_index.core import StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.graph_stores.neo4j import Neo4jGraphStore
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.storage.index_store.redis import RedisIndexStore
import qdrant_client

# Initialize storage backends
qdrant_client = qdrant_client.QdrantClient(
    host="localhost",
    port=6333
)

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name="documents"
)

graph_store = Neo4jGraphStore(
    username="neo4j",
    password="password",
    url="bolt://localhost:7687",
    database="neo4j"
)

docstore = RedisDocumentStore.from_host_and_port(
    host="localhost",
    port=6379,
    namespace="llamacrawl"
)

# Create unified storage context
storage_context = StorageContext.from_defaults(
    vector_store=vector_store,
    graph_store=graph_store,
    docstore=docstore
)
```

### 1.4 Index Creation Pattern

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

# Load documents
documents = SimpleDirectoryReader("data").load_data()

# Create index with storage context
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context,
    show_progress=True
)

# Persist index
index.storage_context.persist(persist_dir="./storage")

# Load existing index
from llama_index.core import load_index_from_storage

storage_context = StorageContext.from_defaults(persist_dir="./storage")
index = load_index_from_storage(storage_context)
```

**Documentation:** https://docs.llamaindex.ai/en/stable/module_guides/indexing/vector_store_guide/

---

## 2. Reader Integration Patterns

### 2.1 FireCrawlWebReader

FireCrawl integration enables web scraping and crawling with AI-optimized markdown output.

**Installation:**
```bash
pip install llama-index-readers-web
```

**Basic Usage:**
```python
from llama_index.readers.web import FireCrawlWebReader
from llama_index.core import SummaryIndex
import os

# Initialize reader
firecrawl_reader = FireCrawlWebReader(
    api_key=os.environ["FIRECRAWL_API_KEY"],
    mode="scrape",  # Options: "scrape", "crawl", "extract"
    params={
        "pageOptions": {
            "onlyMainContent": True
        }
    }
)

# Scrape mode - single page
documents = firecrawl_reader.load_data(url="https://example.com")

# Crawl mode - entire website
firecrawl_reader = FireCrawlWebReader(
    api_key=os.environ["FIRECRAWL_API_KEY"],
    mode="crawl",
    params={
        "crawlerOptions": {
            "maxDepth": 2,
            "limit": 100
        }
    }
)
documents = firecrawl_reader.load_data(url="https://example.com")

# Extract mode - structured data extraction
firecrawl_reader = FireCrawlWebReader(
    api_key=os.environ["FIRECRAWL_API_KEY"],
    mode="extract",
    params={
        "prompt": "Extract all product names and prices",
        "schema": {
            "type": "object",
            "properties": {
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "price": {"type": "number"}
                        }
                    }
                }
            }
        }
    }
)
documents = firecrawl_reader.load_data(url="https://example.com/products")

# Index documents
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
```

**Documentation:** https://docs.firecrawl.dev/integrations/llamaindex

### 2.2 GmailReader

```python
from llama_index.readers.google import GmailReader

# Initialize with OAuth credentials
gmail_reader = GmailReader(
    query="from:important@example.com",
    max_results=10,
    service=None  # Automatically handles OAuth
)

documents = gmail_reader.load_data()
```

**Documentation:** https://llamahub.ai/l/readers/llama-index-readers-google

### 2.3 GitHubRepositoryReader

```python
from llama_index.readers.github import GithubRepositoryReader

github_reader = GithubRepositoryReader(
    owner="run-llama",
    repo="llama_index",
    github_token=os.environ["GITHUB_TOKEN"],
    filter_directories=(
        ["llama-index-core"],
        GithubRepositoryReader.FilterType.INCLUDE
    ),
    filter_file_extensions=(
        [".py"],
        GithubRepositoryReader.FilterType.INCLUDE
    )
)

documents = github_reader.load_data(branch="main")
```

### 2.4 Custom Reader Pattern

```python
from llama_index.core.readers.base import BaseReader
from llama_index.core import Document
from typing import List

class CustomDataReader(BaseReader):
    """Custom reader for specific data source."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def load_data(self, **kwargs) -> List[Document]:
        """Load data and return Document objects."""
        # Fetch data from source
        raw_data = self._fetch_data(**kwargs)

        # Convert to Document objects
        documents = []
        for item in raw_data:
            doc = Document(
                text=item["content"],
                metadata={
                    "source": item["url"],
                    "timestamp": item["date"],
                    "author": item["author"]
                }
            )
            documents.append(doc)

        return documents

    def _fetch_data(self, **kwargs):
        # Implementation specific to data source
        pass
```

**All Available Readers:** https://llamahub.ai/?tab=readers

---

## 3. Storage Backend Integration

### 3.1 Qdrant Vector Store

Qdrant provides high-performance vector similarity search.

**Installation:**
```bash
pip install llama-index-vector-stores-qdrant qdrant-client
```

**Basic Setup:**
```python
import qdrant_client
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext

# Option 1: In-memory (for testing)
client = qdrant_client.QdrantClient(location=":memory:")

# Option 2: Local persistent storage
client = qdrant_client.QdrantClient(path="./qdrant_data")

# Option 3: Remote server
client = qdrant_client.QdrantClient(
    host="localhost",
    port=6333,
    api_key="your-api-key"  # Optional
)

# Create vector store
vector_store = QdrantVectorStore(
    client=client,
    collection_name="documents",
    enable_hybrid=False  # Set True for hybrid search
)

# Use with StorageContext
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Build index
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context
)
```

**Hybrid Search Setup:**
```python
# Must enable hybrid search during initialization
vector_store = QdrantVectorStore(
    client=client,
    collection_name="documents",
    enable_hybrid=True  # Enable from the beginning
)

storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

# Query with hybrid mode
query_engine = index.as_query_engine(
    vector_store_query_mode="hybrid",
    similarity_top_k=10,
    sparse_top_k=12,
    alpha=0.5  # Balance between dense and sparse (0=sparse, 1=dense)
)
```

**Metadata Filtering:**
```python
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

# Create index
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

# Query with metadata filters
filters = MetadataFilters(
    filters=[
        MetadataFilter(key="author", value="John Doe"),
        MetadataFilter(key="date", value="2025-01", operator=">=")
    ]
)

retriever = index.as_retriever(
    similarity_top_k=5,
    filters=filters
)
```

**Async Operations:**
```python
# Create async client
aclient = qdrant_client.AsyncQdrantClient(host="localhost", port=6333)

vector_store = QdrantVectorStore(
    aclient=aclient,
    collection_name="documents"
)

# Async index operations
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
response = await index.aquery("What is LlamaIndex?")
```

**Documentation:**
- Qdrant Integration: https://qdrant.tech/documentation/frameworks/llama-index/
- Hybrid Search: https://docs.llamaindex.ai/en/stable/examples/vector_stores/qdrant_hybrid/
- API Reference: https://docs.llamaindex.ai/en/stable/api_reference/storage/vector_store/qdrant/

### 3.2 Neo4j Graph Store

Neo4j enables knowledge graph construction and querying.

**Installation:**
```bash
pip install llama-index-graph-stores-neo4j neo4j
```

**PropertyGraphIndex Setup:**
```python
from llama_index.core import PropertyGraphIndex
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core.indices.property_graph import (
    SimpleLLMPathExtractor,
    DynamicLLMPathExtractor,
    SchemaLLMPathExtractor,
    ImplicitPathExtractor
)

# Initialize Neo4j graph store
graph_store = Neo4jPropertyGraphStore(
    username="neo4j",
    password="password",
    url="bolt://localhost:7687",
    database="neo4j"
)

# Option 1: Simple entity extraction (exploratory)
kg_extractors = [
    SimpleLLMPathExtractor(
        llm=Settings.llm,
        num_workers=4,
        max_paths_per_chunk=10
    )
]

# Option 2: Dynamic entity extraction with types
kg_extractors = [
    DynamicLLMPathExtractor(
        llm=Settings.llm,
        allowed_entity_types=["Person", "Organization", "Location", "Product"],
        allowed_relation_types=["works_for", "located_in", "produces"]
    )
]

# Option 3: Schema-based extraction (production)
kg_extractors = [
    SchemaLLMPathExtractor(
        llm=Settings.llm,
        possible_entities=["Person", "Organization", "Product"],
        possible_relations=["WORKS_FOR", "MANUFACTURES"],
        schema={
            "Person": ["WORKS_FOR"],
            "Organization": ["MANUFACTURES"]
        },
        strict=True  # Enforce exact schema
    )
]

# Create PropertyGraph index
index = PropertyGraphIndex.from_documents(
    documents,
    property_graph_store=graph_store,
    kg_extractors=kg_extractors,
    show_progress=True
)

# Query the knowledge graph
query_engine = index.as_query_engine(
    include_text=True,  # Include original text
    response_mode="tree_summarize"
)

response = query_engine.query("What companies does John work for?")
```

**Text-to-Cypher Pattern:**
```python
from llama_index.core.query_engine import KnowledgeGraphQueryEngine

# Use existing Neo4j graph
kg_query_engine = KnowledgeGraphQueryEngine(
    storage_context=storage_context,
    llm=Settings.llm,
    verbose=True
)

# Natural language to Cypher
response = kg_query_engine.query(
    "Show me all people who work for organizations in California"
)
```

**Documentation:**
- Neo4j Integration: https://neo4j.com/labs/genai-ecosystem/llamaindex/
- PropertyGraph Guide: https://docs.llamaindex.ai/en/stable/module_guides/indexing/lpg_index_guide/
- Building Knowledge Graphs: https://docs.llamaindex.ai/en/latest/examples/cookbooks/build_knowledge_graph_with_neo4j_llamacloud/
- Knowledge Graph Agents: https://neo4j.com/blog/knowledge-graph/knowledge-graph-agents-llamaindex/

### 3.3 Redis for Caching and Document Store

Redis provides caching, document storage, and vector storage capabilities.

**Installation:**
```bash
pip install llama-index-storage-docstore-redis
pip install llama-index-storage-index-store-redis
pip install llama-index-vector-stores-redis
```

**Redis with Ingestion Pipeline:**
```python
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.vector_stores.redis import RedisVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Initialize Redis components
docstore = RedisDocumentStore.from_host_and_port(
    host="localhost",
    port=6379,
    namespace="llamacrawl_docs"
)

vector_store = RedisVectorStore(
    redis_url="redis://localhost:6379",
    index_name="llamacrawl_vectors",
    index_args={
        "algorithm": "FLAT",  # or "HNSW" for approximate search
        "distance_metric": "COSINE"
    }
)

cache = IngestionCache(
    cache=RedisDocumentStore.from_host_and_port(
        host="localhost",
        port=6379,
        namespace="llamacrawl_cache"
    )
)

# Create ingestion pipeline with caching
pipeline = IngestionPipeline(
    transformations=[
        SentenceSplitter(chunk_size=512, chunk_overlap=20),
        HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    ],
    docstore=docstore,
    vector_store=vector_store,
    cache=cache
)

# Run pipeline - uses cache on subsequent runs
nodes = pipeline.run(documents=documents, show_progress=True)

# Create index from vector store
index = VectorStoreIndex.from_vector_store(vector_store)
```

**Docker Setup for Redis:**
```bash
docker run -d \
  --name redis-stack \
  -p 6379:6379 \
  -p 8001:8001 \
  redis/redis-stack:latest
```

**Documentation:**
- Redis Ingestion Pipeline: https://docs.llamaindex.ai/en/stable/examples/ingestion/redis_ingestion_pipeline/
- Redis Vector Store: https://docs.llamaindex.ai/en/stable/examples/vector_stores/RedisIndexDemo/

---

## 4. Embedding Configuration

### 4.1 External Embedding Service Pattern

For the llamacrawl project using TEI (Text Embeddings Inference):

```python
from llama_index.core.embeddings import BaseEmbedding
from typing import List
import requests

class TEIEmbedding(BaseEmbedding):
    """Custom embedding class for TEI service."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        model_name: str = "BAAI/bge-large-en-v1.5",
        embed_batch_size: int = 10
    ):
        super().__init__(
            model_name=model_name,
            embed_batch_size=embed_batch_size
        )
        self.base_url = base_url

    def _get_query_embedding(self, query: str) -> List[float]:
        """Get embedding for a single query."""
        response = requests.post(
            f"{self.base_url}/embed",
            json={"inputs": query}
        )
        response.raise_for_status()
        return response.json()

    def _get_text_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text."""
        return self._get_query_embedding(text)

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        response = requests.post(
            f"{self.base_url}/embed",
            json={"inputs": texts}
        )
        response.raise_for_status()
        return response.json()

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Async get query embedding."""
        # Implement async version if needed
        return self._get_query_embedding(query)

# Use with Settings
from llama_index.core import Settings

Settings.embed_model = TEIEmbedding(
    base_url="http://localhost:8080",
    model_name="BAAI/bge-large-en-v1.5"
)
```

### 4.2 Built-in Embedding Models

**OpenAI:**
```python
from llama_index.embeddings.openai import OpenAIEmbedding

Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",
    dimensions=512  # Optional: reduce dimensions
)
```

**HuggingFace Local:**
```python
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5",
    device="cuda"  # or "cpu"
)
```

**Ollama:**
```python
from llama_index.embeddings.ollama import OllamaEmbedding

Settings.embed_model = OllamaEmbedding(
    model_name="nomic-embed-text",
    base_url="http://localhost:11434"
)
```

**Documentation:**
- Embeddings Guide: https://docs.llamaindex.ai/en/stable/module_guides/models/embeddings/
- Custom Embeddings: https://docs.llamaindex.ai/en/stable/examples/embeddings/custom_embeddings/

---

## 5. Ingestion Pipeline Patterns

### 5.1 Basic Ingestion Pipeline

```python
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import (
    TitleExtractor,
    SummaryExtractor,
    KeywordExtractor,
    QuestionsAnsweredExtractor
)

# Define transformation pipeline
pipeline = IngestionPipeline(
    transformations=[
        SentenceSplitter(chunk_size=512, chunk_overlap=20),
        TitleExtractor(llm=Settings.llm),
        KeywordExtractor(llm=Settings.llm, keywords=10),
        SummaryExtractor(llm=Settings.llm, summaries=["self"]),
        Settings.embed_model
    ]
)

# Run pipeline
nodes = pipeline.run(documents=documents, show_progress=True)

# Create index from nodes
index = VectorStoreIndex(nodes, storage_context=storage_context)
```

### 5.2 Production Pipeline with Caching

```python
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.storage.docstore.redis import RedisDocumentStore

# Setup caching
cache = IngestionCache(
    cache=RedisDocumentStore.from_host_and_port(
        host="localhost",
        port=6379,
        namespace="pipeline_cache"
    ),
    collection="ingestion_cache"
)

# Create pipeline with persistence
pipeline = IngestionPipeline(
    transformations=[
        SentenceSplitter(chunk_size=512, chunk_overlap=20),
        Settings.embed_model
    ],
    docstore=docstore,
    vector_store=vector_store,
    cache=cache
)

# First run - processes all documents
nodes = pipeline.run(documents=documents)

# Subsequent runs - only process new/changed documents
new_documents = load_new_documents()
nodes = pipeline.run(documents=new_documents)  # Uses cache for existing docs
```

### 5.3 Advanced Chunking Strategies

**Semantic Chunking:**
```python
from llama_index.core.node_parser import SemanticSplitterNodeParser

semantic_splitter = SemanticSplitterNodeParser(
    buffer_size=1,  # Number of sentences to group
    embed_model=Settings.embed_model,
    breakpoint_percentile_threshold=95  # Sensitivity for semantic breaks
)

pipeline = IngestionPipeline(
    transformations=[
        semantic_splitter,
        Settings.embed_model
    ]
)
```

**Sentence Window:**
```python
from llama_index.core.node_parser import SentenceWindowNodeParser

sentence_window_parser = SentenceWindowNodeParser.from_defaults(
    window_size=3,  # Sentences on each side
    window_metadata_key="window",
    original_text_metadata_key="original_sentence"
)

pipeline = IngestionPipeline(
    transformations=[
        sentence_window_parser,
        Settings.embed_model
    ]
)
```

**Hierarchical Chunking:**
```python
from llama_index.core.node_parser import HierarchicalNodeParser

hierarchical_parser = HierarchicalNodeParser.from_defaults(
    chunk_sizes=[2048, 512, 128]  # Multiple hierarchy levels
)

pipeline = IngestionPipeline(
    transformations=[
        hierarchical_parser,
        Settings.embed_model
    ]
)
```

**Documentation:**
- Ingestion Pipeline: https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/
- Chunking Strategies: https://medium.com/@bavalpreetsinghh/llamaindex-chunking-strategies-for-large-language-models-part-1-ded1218cfd30
- Semantic Chunking: https://docs.llamaindex.ai/en/stable/examples/node_parsers/semantic_chunking/

---

## 6. Query Engine Patterns

### 6.1 Basic Vector Query Engine

```python
# Simple query engine
query_engine = index.as_query_engine(
    similarity_top_k=5,
    response_mode="compact"  # Options: compact, tree_summarize, simple_summarize
)

response = query_engine.query("What is LlamaIndex?")
print(response.response)
print(response.source_nodes)  # Retrieved context
```

### 6.2 Hybrid Search with Reranking

```python
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever

# Setup hybrid retriever
retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=20,  # Retrieve more candidates
    vector_store_query_mode="hybrid"  # Requires enable_hybrid=True
)

# Add reranker
reranker = SentenceTransformerRerank(
    model="BAAI/bge-reranker-base",
    top_n=5  # Final number of results
)

# Build query engine
query_engine = RetrieverQueryEngine.from_args(
    retriever=retriever,
    node_postprocessors=[reranker],
    response_mode="tree_summarize"
)

response = query_engine.query("Complex query requiring hybrid search")
```

### 6.3 Custom Hybrid Retriever

```python
from llama_index.core.retrievers import (
    VectorIndexRetriever,
    KeywordTableSimpleRetriever
)
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core import get_response_synthesizer
from typing import List

class HybridRetriever:
    """Custom hybrid retriever combining vector and keyword search."""

    def __init__(
        self,
        vector_retriever: VectorIndexRetriever,
        keyword_retriever: KeywordTableSimpleRetriever,
        mode: str = "OR"  # OR, AND
    ):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        self.mode = mode

    def retrieve(self, query_str: str) -> List:
        """Retrieve from both and combine results."""
        vector_nodes = self.vector_retriever.retrieve(query_str)
        keyword_nodes = self.keyword_retriever.retrieve(query_str)

        # Combine and deduplicate
        all_nodes = {n.node.node_id: n for n in vector_nodes}
        for n in keyword_nodes:
            if n.node.node_id not in all_nodes:
                all_nodes[n.node.node_id] = n
            else:
                # Average scores
                all_nodes[n.node.node_id].score = (
                    all_nodes[n.node.node_id].score + n.score
                ) / 2

        # Sort by score
        return sorted(all_nodes.values(), key=lambda x: x.score, reverse=True)

# Use custom retriever
vector_retriever = VectorIndexRetriever(index=vector_index, similarity_top_k=10)
keyword_retriever = KeywordTableSimpleRetriever(index=keyword_index)

custom_retriever = HybridRetriever(vector_retriever, keyword_retriever)

query_engine = RetrieverQueryEngine(
    retriever=custom_retriever,
    response_synthesizer=get_response_synthesizer(response_mode="tree_summarize")
)
```

### 6.4 Router Query Engine

Routes queries to different specialized engines.

```python
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import PydanticSingleSelector
from llama_index.core.tools import QueryEngineTool

# Create specialized query engines
vector_query_engine = vector_index.as_query_engine(similarity_top_k=5)
graph_query_engine = graph_index.as_query_engine()

# Define tools
vector_tool = QueryEngineTool.from_defaults(
    query_engine=vector_query_engine,
    description="Useful for semantic search over documents. Use for factual questions."
)

graph_tool = QueryEngineTool.from_defaults(
    query_engine=graph_query_engine,
    description="Useful for relationship queries. Use for questions about connections."
)

# Create router
router_query_engine = RouterQueryEngine(
    selector=PydanticSingleSelector.from_defaults(),
    query_engine_tools=[vector_tool, graph_tool],
    verbose=True
)

# Router automatically selects appropriate engine
response = router_query_engine.query("How are Company A and Company B related?")
```

### 6.5 Sub-Question Query Engine

Decomposes complex queries into sub-questions.

```python
from llama_index.core.query_engine import SubQuestionQueryEngine
from llama_index.core.tools import QueryEngineTool

# Create query engines for different data sources
doc_query_engine = doc_index.as_query_engine()
code_query_engine = code_index.as_query_engine()

# Define tools
doc_tool = QueryEngineTool.from_defaults(
    query_engine=doc_query_engine,
    description="Documentation about the project"
)

code_tool = QueryEngineTool.from_defaults(
    query_engine=code_query_engine,
    description="Source code of the project"
)

# Create sub-question engine
sub_question_engine = SubQuestionQueryEngine.from_defaults(
    query_engine_tools=[doc_tool, code_tool],
    verbose=True
)

# Automatically breaks down into sub-questions
response = sub_question_engine.query(
    "How does the authentication system work and where is it implemented?"
)
```

### 6.6 Alpha Tuning for Hybrid Search

Balance dense vs sparse retrieval:

```python
# Experiment with different alpha values
# alpha=0.0: Pure sparse (BM25/keyword)
# alpha=0.5: Balanced hybrid
# alpha=1.0: Pure dense (vector)

for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
    query_engine = index.as_query_engine(
        vector_store_query_mode="hybrid",
        similarity_top_k=10,
        alpha=alpha
    )
    response = query_engine.query("test query")
    # Evaluate results
```

**Documentation:**
- Custom Retrievers: https://docs.llamaindex.ai/en/stable/examples/query_engine/CustomRetrievers/
- Router Query Engine: https://docs.llamaindex.ai/en/stable/examples/query_engine/RouterQueryEngine/
- Sub-Question Engine: https://docs.llamaindex.ai/en/stable/examples/query_engine/sub_question_query_engine/
- Hybrid Search Alpha Tuning: https://www.llamaindex.ai/blog/llamaindex-enhancing-retrieval-performance-with-alpha-tuning-in-hybrid-search-in-rag-135d0c9b8a00

---

## 7. Complete Integration Examples

### 7.1 Full Stack RAG Pipeline

```python
import os
from llama_index.core import Settings, VectorStoreIndex, StorageContext
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.web import FireCrawlWebReader
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.core.postprocessor import SentenceTransformerRerank
import qdrant_client

# 1. Configure global settings
Settings.llm = OpenAI(model="gpt-4", temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
Settings.chunk_size = 512
Settings.chunk_overlap = 20

# 2. Initialize storage backends
qdrant_client = qdrant_client.QdrantClient(host="localhost", port=6333)

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name="llamacrawl",
    enable_hybrid=True
)

graph_store = Neo4jPropertyGraphStore(
    username="neo4j",
    password="password",
    url="bolt://localhost:7687"
)

docstore = RedisDocumentStore.from_host_and_port(
    host="localhost",
    port=6379,
    namespace="llamacrawl"
)

storage_context = StorageContext.from_defaults(
    vector_store=vector_store,
    graph_store=graph_store,
    docstore=docstore
)

# 3. Setup ingestion pipeline
cache = IngestionCache(
    cache=RedisDocumentStore.from_host_and_port(
        host="localhost",
        port=6379,
        namespace="cache"
    )
)

pipeline = IngestionPipeline(
    transformations=[
        SentenceSplitter(chunk_size=512, chunk_overlap=20),
        Settings.embed_model
    ],
    docstore=docstore,
    vector_store=vector_store,
    cache=cache
)

# 4. Load documents
firecrawl_reader = FireCrawlWebReader(
    api_key=os.environ["FIRECRAWL_API_KEY"],
    mode="crawl",
    params={"crawlerOptions": {"maxDepth": 2, "limit": 100}}
)

documents = firecrawl_reader.load_data(url="https://docs.llamaindex.ai")

# 5. Process documents
nodes = pipeline.run(documents=documents, show_progress=True)

# 6. Create index
index = VectorStoreIndex(nodes, storage_context=storage_context)

# 7. Build query engine with reranking
reranker = SentenceTransformerRerank(
    model="BAAI/bge-reranker-base",
    top_n=5
)

query_engine = index.as_query_engine(
    similarity_top_k=20,
    vector_store_query_mode="hybrid",
    alpha=0.5,
    node_postprocessors=[reranker],
    response_mode="tree_summarize"
)

# 8. Query
response = query_engine.query("How do I build a RAG pipeline with LlamaIndex?")
print(response.response)

# 9. Persist
index.storage_context.persist(persist_dir="./storage")
```

### 7.2 Knowledge Graph RAG Pipeline

```python
from llama_index.core import PropertyGraphIndex
from llama_index.core.indices.property_graph import (
    SchemaLLMPathExtractor,
    ImplicitPathExtractor
)

# Define entity schema
kg_extractors = [
    SchemaLLMPathExtractor(
        llm=Settings.llm,
        possible_entities=["Person", "Organization", "Technology", "Concept"],
        possible_relations=["USES", "CREATES", "WORKS_FOR", "RELATED_TO"],
        schema={
            "Person": ["WORKS_FOR", "CREATES"],
            "Organization": ["USES", "CREATES"],
            "Technology": ["RELATED_TO"]
        },
        strict=True
    ),
    ImplicitPathExtractor()
]

# Create PropertyGraph index
graph_index = PropertyGraphIndex.from_documents(
    documents,
    property_graph_store=graph_store,
    kg_extractors=kg_extractors,
    show_progress=True
)

# Create hybrid query engine (graph + vector)
from llama_index.core.query_engine import ComposableQueryEngine

graph_query_engine = graph_index.as_query_engine(
    include_text=True,
    response_mode="tree_summarize"
)

vector_query_engine = index.as_query_engine(
    similarity_top_k=5
)

# Router for hybrid querying
router_engine = RouterQueryEngine(
    selector=PydanticSingleSelector.from_defaults(),
    query_engine_tools=[
        QueryEngineTool.from_defaults(
            query_engine=graph_query_engine,
            description="Knowledge graph for relationship queries"
        ),
        QueryEngineTool.from_defaults(
            query_engine=vector_query_engine,
            description="Vector search for semantic queries"
        )
    ]
)
```

### 7.3 Multi-Source RAG with Readers

```python
from llama_index.readers.web import FireCrawlWebReader
from llama_index.readers.google import GmailReader
from llama_index.readers.github import GithubRepositoryReader

# Multiple data sources
sources = []

# Web content
firecrawl = FireCrawlWebReader(
    api_key=os.environ["FIRECRAWL_API_KEY"],
    mode="scrape"
)
web_docs = firecrawl.load_data(url="https://example.com")
sources.extend(web_docs)

# Gmail
gmail = GmailReader(query="from:team@example.com", max_results=50)
email_docs = gmail.load_data()
sources.extend(email_docs)

# GitHub
github = GithubRepositoryReader(
    owner="company",
    repo="project",
    github_token=os.environ["GITHUB_TOKEN"],
    filter_file_extensions=([".py", ".md"], GithubRepositoryReader.FilterType.INCLUDE)
)
code_docs = github.load_data(branch="main")
sources.extend(code_docs)

# Process all sources
nodes = pipeline.run(documents=sources, show_progress=True)
index = VectorStoreIndex(nodes, storage_context=storage_context)

# Create source-aware query engine
from llama_index.core.query_engine import SubQuestionQueryEngine

web_index = VectorStoreIndex([n for n in nodes if n.metadata.get("source") == "web"])
email_index = VectorStoreIndex([n for n in nodes if n.metadata.get("source") == "gmail"])
code_index = VectorStoreIndex([n for n in nodes if n.metadata.get("source") == "github"])

query_engine = SubQuestionQueryEngine.from_defaults(
    query_engine_tools=[
        QueryEngineTool.from_defaults(
            query_engine=web_index.as_query_engine(),
            description="Web documentation"
        ),
        QueryEngineTool.from_defaults(
            query_engine=email_index.as_query_engine(),
            description="Email communications"
        ),
        QueryEngineTool.from_defaults(
            query_engine=code_index.as_query_engine(),
            description="Source code"
        )
    ]
)
```

---

## 8. Production Best Practices

### 8.1 Error Handling and Retries

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class RobustRAGPipeline:
    def __init__(self, index, max_retries=3):
        self.index = index
        self.max_retries = max_retries

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def query(self, query_str: str):
        """Query with automatic retries."""
        try:
            response = self.index.as_query_engine().query(query_str)
            return response
        except Exception as e:
            print(f"Query failed: {e}")
            raise

    def safe_ingest(self, documents):
        """Ingest with error handling."""
        successful = []
        failed = []

        for doc in documents:
            try:
                nodes = self.pipeline.run(documents=[doc])
                successful.append(doc)
            except Exception as e:
                print(f"Failed to ingest {doc.metadata.get('source')}: {e}")
                failed.append((doc, str(e)))

        return successful, failed
```

### 8.2 Monitoring and Observability

```python
import logging
from datetime import datetime

class ObservableQueryEngine:
    def __init__(self, query_engine):
        self.query_engine = query_engine
        self.logger = logging.getLogger(__name__)

    def query(self, query_str: str):
        """Query with logging."""
        start_time = datetime.now()

        self.logger.info(f"Query started: {query_str}")

        try:
            response = self.query_engine.query(query_str)

            duration = (datetime.now() - start_time).total_seconds()

            self.logger.info(
                f"Query completed in {duration}s",
                extra={
                    "query": query_str,
                    "duration": duration,
                    "num_sources": len(response.source_nodes),
                    "response_length": len(response.response)
                }
            )

            return response

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(
                f"Query failed after {duration}s: {e}",
                extra={"query": query_str, "error": str(e)}
            )
            raise
```

### 8.3 Evaluation Framework

```python
from llama_index.core.evaluation import (
    FaithfulnessEvaluator,
    RelevancyEvaluator,
    CorrectnessEvaluator
)

# Setup evaluators
faithfulness_evaluator = FaithfulnessEvaluator(llm=Settings.llm)
relevancy_evaluator = RelevancyEvaluator(llm=Settings.llm)
correctness_evaluator = CorrectnessEvaluator(llm=Settings.llm)

# Evaluate query
query = "What is LlamaIndex?"
response = query_engine.query(query)

# Check faithfulness (response grounded in context)
faith_result = faithfulness_evaluator.evaluate_response(response=response)
print(f"Faithfulness: {faith_result.passing}")

# Check relevancy (context relevant to query)
relevancy_result = relevancy_evaluator.evaluate_response(
    query=query,
    response=response
)
print(f"Relevancy: {relevancy_result.passing}")

# Check correctness (against reference answer)
reference_answer = "LlamaIndex is a data framework for LLM applications"
correctness_result = correctness_evaluator.evaluate(
    query=query,
    response=response.response,
    reference=reference_answer
)
print(f"Correctness: {correctness_result.score}")
```

### 8.4 Batch Processing

```python
from typing import List
import asyncio

class BatchRAGProcessor:
    def __init__(self, index, batch_size: int = 10):
        self.index = index
        self.batch_size = batch_size

    async def process_queries_async(self, queries: List[str]):
        """Process multiple queries concurrently."""
        query_engine = self.index.as_query_engine()

        tasks = []
        for query in queries:
            tasks.append(query_engine.aquery(query))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for query, response in zip(queries, responses):
            if isinstance(response, Exception):
                results.append({"query": query, "error": str(response)})
            else:
                results.append({
                    "query": query,
                    "response": response.response,
                    "sources": [n.metadata for n in response.source_nodes]
                })

        return results

    def batch_ingest(self, documents: List, batch_size: int = None):
        """Ingest documents in batches."""
        batch_size = batch_size or self.batch_size

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            nodes = self.pipeline.run(documents=batch, show_progress=True)
            print(f"Processed batch {i//batch_size + 1}")
```

### 8.5 Configuration Management

```python
from pydantic import BaseModel, Field
from typing import Optional
import yaml

class RAGConfig(BaseModel):
    """Configuration for RAG pipeline."""

    # LLM settings
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.1

    # Embedding settings
    embed_model: str = "text-embedding-3-small"
    embed_batch_size: int = 10

    # Chunking settings
    chunk_size: int = 512
    chunk_overlap: int = 20

    # Retrieval settings
    similarity_top_k: int = 5
    rerank_top_n: int = 3

    # Storage settings
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    neo4j_url: str = "bolt://localhost:7687"
    redis_host: str = "localhost"
    redis_port: int = 6379

    # API keys
    openai_api_key: Optional[str] = None
    firecrawl_api_key: Optional[str] = None

    @classmethod
    def from_yaml(cls, path: str):
        """Load config from YAML file."""
        with open(path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)

    def to_yaml(self, path: str):
        """Save config to YAML file."""
        with open(path, 'w') as f:
            yaml.dump(self.dict(), f)

# Usage
config = RAGConfig.from_yaml("config.yaml")

Settings.llm = OpenAI(model=config.llm_model, temperature=config.llm_temperature)
Settings.embed_model = OpenAIEmbedding(model=config.embed_model)
Settings.chunk_size = config.chunk_size
```

---

## 9. Key Takeaways

### 9.1 Architecture Decisions

1. **Use Settings for global configuration** - Replace ServiceContext with the modern Settings API
2. **StorageContext for multiple backends** - Unify vector, graph, and document stores
3. **Ingestion Pipeline for production** - Enable caching and document management
4. **Hybrid search for better recall** - Combine dense and sparse retrieval

### 9.2 Performance Optimization

1. **Enable caching** - Use Redis for ingestion pipeline caching
2. **Batch processing** - Process documents and queries in batches
3. **Async operations** - Use async methods for concurrent operations
4. **Proper chunking** - Choose appropriate chunking strategy for your data
5. **Reranking** - Add reranker to improve final results

### 9.3 Common Patterns for llamacrawl

1. **FireCrawl + Qdrant + Neo4j stack**
   - FireCrawl for web data ingestion
   - Qdrant for vector similarity search with hybrid mode
   - Neo4j for knowledge graph relationships
   - Redis for caching and document store

2. **TEI custom embeddings**
   - Implement BaseEmbedding for TEI service
   - Configure in global Settings
   - Use with ingestion pipeline

3. **Multi-source ingestion**
   - Combine FireCrawl, Gmail, GitHub readers
   - Use SubQuestionQueryEngine for source-aware querying
   - Tag documents with source metadata

4. **Production query engine**
   - Hybrid search with alpha tuning
   - Sentence transformer reranking
   - Error handling and retries
   - Monitoring and evaluation

---

## 10. Additional Resources

### Official Documentation
- LlamaIndex Docs: https://docs.llamaindex.ai/en/stable/
- API Reference: https://docs.llamaindex.ai/en/stable/api_reference/
- Examples: https://docs.llamaindex.ai/en/stable/examples/
- LlamaHub: https://llamahub.ai/

### Integration Guides
- Qdrant: https://qdrant.tech/documentation/frameworks/llama-index/
- Neo4j: https://neo4j.com/labs/genai-ecosystem/llamaindex/
- FireCrawl: https://docs.firecrawl.dev/integrations/llamaindex

### Best Practices
- Production RAG: https://docs.llamaindex.ai/en/stable/optimizing/production_rag/
- Basic Strategies: https://docs.llamaindex.ai/en/stable/optimizing/basic_strategies/basic_strategies/
- Evaluation: https://docs.llamaindex.ai/en/stable/module_guides/evaluating/

### Community Resources
- GitHub: https://github.com/run-llama/llama_index
- Discord: https://discord.gg/dGcwcsnxhU
- Blog: https://www.llamaindex.ai/blog

---

**Document Version:** 1.0
**Last Updated:** 2025-09-30
**Target Project:** llamacrawl RAG pipeline
