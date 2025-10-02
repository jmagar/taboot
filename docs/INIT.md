# LlamaCrawl - RAG pipeline built with LlamaIndex


Ingesting/crawling data from:
    - Gmail: https://llamahub.ai/l/readers/llama-index-readers-google
    - Google Calendar: https://llamahub.ai/l/readers/llama-index-readers-google
    - Google Docs: https://llamahub.ai/l/readers/llama-index-readers-google
    - Google Drive: https://llamahub.ai/l/readers/llama-index-readers-google
    - Google Keep: https://llamahub.ai/l/readers/llama-index-readers-google
    - Youtube Transcripts: https://llamahub.ai/l/readers/llama-index-readers-youtube-transcript
    - Databases: https://llamahub.ai/l/readers/llama-index-readers-database
    - PDFs: https://llamahub.ai/l/readers/llama-index-readers-smart-pdf-loader
    - Remote Page/Files: https://llamahub.ai/l/readers/llama-index-readers-remote
    - Remote Depth: https://llamahub.ai/l/readers/llama-index-readers-remote-depth
    - Docstring Walker: https://llamahub.ai/l/readers/llama-index-readers-docstring-walker
    - Qdrant: https://llamahub.ai/l/readers/llama-index-readers-qdrant
    - Feedly: https://llamahub.ai/l/readers/llama-index-readers-feedly-rss
    - Memos: https://llamahub.ai/l/readers/llama-index-readers-memos
    - Reddit: https://llamahub.ai/l/readers/llama-index-readers-reddit
    - Github: https://llamahub.ai/l/readers/llama-index-readers-github
    - Web: https://llamahub.ai/l/readers/llama-index-readers-web
    - LlamaParse: https://llamahub.ai/l/readers/llama-index-readers-llama-parse **
    - JSON: https://llamahub.ai/l/readers/llama-index-readers-json
    - ElasticSearch: https://llamahub.ai/l/readers/llama-index-readers-elasticsearch

Generating embeddings with: Qwen 3 0.6b via
Huggingface Text Embeddings Inference: https://llamahub.ai/l/embeddings/llama-index-embeddings-huggingface or https://llamahub.ai/l/embeddings/llama-index-embeddings-huggingface-api -- not sure what's different

Vector stores via
Qdrant: https://llamahub.ai/l/vector_stores/llama-index-vector-stores-qdrant

Graph stores via
Neo4j: https://llamahub.ai/l/graph_stores/llama-index-graph-stores-neo4j

Storage via
Redis Kv: https://llamahub.ai/l/storage/llama-index-storage-kvstore-redis

Retrieval via
BM25: https://llamahub.ai/l/retrievers/llama-index-retrievers-bm25

Post-processing and reranking with Qwen3-Reranker-0.6B-seq-cls https://huggingface.co/tomaarsen/Qwen3-Reranker-0.6B-seq-cls
via
Huggingface Text Embeddings Inference
Synthesis via Ollama

Deployed via Docker Compose with Docker Context to:
   - Server: steamy-wsl
        - @docker-compose.yaml


Code