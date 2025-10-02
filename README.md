# LlamaCrawl

A multi-source RAG (Retrieval Augmented Generation) pipeline built on LlamaIndex that ingests data from web content, GitHub, Reddit, Gmail, and Elasticsearch, stores it in vector and graph databases, and provides intelligent query capabilities with source attribution.

## Features

- **Multi-Source Data Ingestion**: Web (Firecrawl), GitHub, Reddit, Gmail, Elasticsearch
- **Incremental Sync**: Smart synchronization with deduplication and cursor-based updates
- **Hybrid Storage**: Qdrant for vectors, Neo4j for knowledge graphs, Redis for state management
- **Advanced Retrieval**: Vector search + graph traversal + reranking for optimal results
- **Source Attribution**: Every answer includes citations with links to source documents
- **Self-Hosted Infrastructure**: Complete Docker Compose stack with GPU acceleration

## Quick Start

### Prerequisites

- Python 3.11+
- Docker with Docker Compose
- NVIDIA GPU (for embeddings and LLM synthesis)
- UV package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd llamacrawl

# Install dependencies
uv sync

# Copy configuration templates
cp .env.example .env
cp config.example.yaml config.yaml

# Edit configurations with your credentials
$EDITOR .env
$EDITOR config.yaml

# Deploy infrastructure (to remote GPU server)
docker --context docker-mcp-steamy-wsl compose up -d

# Wait for services to be healthy
docker --context docker-mcp-steamy-wsl compose ps

# Initialize storage backends
uv run llamacrawl init

# Verify installation
uv run llamacrawl status
```

### Basic Usage

```bash
# Ingest data from a source
uv run llamacrawl ingest firecrawl

# Query the RAG system
uv run llamacrawl query "What are the latest authentication changes?"

# Query with filters
uv run llamacrawl query "bug reports" --sources github,reddit --after 2024-01-01

# Check system status
uv run llamacrawl status
```

## Architecture

LlamaCrawl consists of three main layers:

1. **Data Ingestion**: Readers load data from multiple sources, documents are chunked, embedded, and stored with deduplication
2. **Storage**: Qdrant (vectors), Neo4j (knowledge graph), Redis (state/cache)
3. **Retrieval**: Hybrid search combining vector similarity, metadata filters, graph traversal, and reranking

```
┌─────────────────────────────────────────────────────────────┐
│                      LlamaCrawl CLI                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                 LlamaIndex Core Engine                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Readers    │  │  Embeddings  │  │  Synthesis   │      │
│  │   (5 types)  │  │     (TEI)    │  │   (Ollama)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼────┐  ┌──────▼──────┐  ┌───▼────┐
│ Qdrant │  │    Neo4j    │  │ Redis  │
│ Vector │  │    Graph    │  │ State  │
│  Store │  │    Store    │  │ Cache  │
└────────┘  └─────────────┘  └────────┘
```

## Data Sources

- **Firecrawl**: Web scraping with configurable crawl depth and page limits
- **GitHub**: Repositories, issues, pull requests, discussions with incremental sync
- **Reddit**: Posts and comments from configured subreddits
- **Gmail**: Email messages and threads via OAuth 2.0
- **Elasticsearch**: Bulk import from existing indices

## Documentation

- [Setup Guide](docs/setup.md) - Infrastructure deployment and environment setup
- [Configuration](docs/configuration.md) - Detailed configuration reference
- [Usage Guide](docs/usage.md) - CLI commands and common workflows
- [Architecture](docs/architecture.md) - System design and data flow

## Technology Stack

- **Framework**: LlamaIndex for RAG orchestration
- **Vector Database**: Qdrant with Qwen3-Embedding-0.6B (1024-dim vectors)
- **Graph Database**: Neo4j for entity relationships
- **Cache/State**: Redis for deduplication and cursor management
- **Embeddings**: TEI (Text Embeddings Inference) with GPU acceleration
- **Reranking**: TEI with Qwen3-Reranker-0.6B
- **LLM**: Ollama with llama3.1:8b for answer synthesis
- **CLI**: Typer for command-line interface

## Contributing

This is currently a personal project. Contributions, issues, and feature requests are welcome through GitHub.

## License

[Your License Here]

## Support

For questions and support, please open an issue on GitHub.
