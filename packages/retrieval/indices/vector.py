"""VectorStoreIndex implementation over Qdrant."""


from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient


def create_vector_index(
    qdrant_url: str,
    collection_name: str,
    embedding_dim: int = 1024,
    qdrant_client: QdrantClient | None = None
) -> VectorStoreIndex:
    """
    Create VectorStoreIndex backed by Qdrant.

    Args:
        qdrant_url: Qdrant server URL
        collection_name: Collection name
        embedding_dim: Embedding vector dimension
        qdrant_client: Optional existing Qdrant client

    Returns:
        VectorStoreIndex instance
    """
    # Create or use existing Qdrant client
    client = qdrant_client or QdrantClient(url=qdrant_url)

    # Create Qdrant vector store
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        prefer_grpc=False
    )

    # Create storage context
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )

    # Create vector index
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context
    )

    return index
