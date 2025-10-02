"""Document chunking strategies using LlamaIndex transformations.

This module provides chunking functionality for breaking documents into
smaller, searchable chunks using token-based splitting with sentence awareness.
"""


from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode

from llamacrawl.config import IngestionConfig
from llamacrawl.models.document import Document


class ChunkingStrategy:
    """Strategy for chunking documents into smaller pieces.

    Uses LlamaIndex SentenceSplitter for token-based chunking with
    sentence awareness. Preserves metadata across chunks and adds
    chunk-specific metadata.

    Attributes:
        chunk_size: Size of chunks in tokens (not characters)
        chunk_overlap: Number of overlapping tokens between chunks
        splitter: LlamaIndex SentenceSplitter instance
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        """Initialize chunking strategy.

        Args:
            chunk_size: Size of chunks in tokens (default: 512)
            chunk_overlap: Number of overlapping tokens (default: 50)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=" ",  # Split on spaces by default
        )

    def chunk_document(self, document: Document) -> list[Document]:
        """Split a document into chunks.

        Converts the custom Document model to LlamaIndex Document,
        performs chunking via SentenceSplitter, then converts chunks
        back to custom Document models with preserved metadata.

        Args:
            document: Document to chunk

        Returns:
            List of chunked Document objects with chunk metadata

        Notes:
            - Very small documents (< chunk_size) remain unchanged
            - Each chunk preserves original metadata
            - Adds chunk_index and total_chunks to metadata
            - Chunks are independently searchable
        """
        # Convert to LlamaIndex Document
        llama_doc = LlamaDocument(
            text=document.content,
            metadata={
                "doc_id": document.doc_id,
                "title": document.title,
                "content_hash": document.content_hash,
                "source_type": document.metadata.source_type,
                "source_url": document.metadata.source_url,
                "timestamp": document.metadata.timestamp.isoformat(),
                **document.metadata.extra,
            },
        )

        # Perform chunking using SentenceSplitter
        nodes: list[BaseNode] = self.splitter.get_nodes_from_documents([llama_doc])

        # If document is smaller than chunk_size, return as-is
        if len(nodes) <= 1:
            return [document]

        # Convert nodes back to Document models
        total_chunks = len(nodes)
        chunked_docs: list[Document] = []

        for chunk_idx, node in enumerate(nodes):
            # Create chunk metadata by extending original metadata
            chunk_metadata = document.metadata.model_copy(deep=True)
            chunk_metadata.extra["chunk_index"] = chunk_idx
            chunk_metadata.extra["total_chunks"] = total_chunks

            # Create new Document for chunk
            chunk_doc = Document(
                doc_id=f"{document.doc_id}_chunk_{chunk_idx}",
                title=document.title,  # Preserve original title
                content=node.get_content(),
                content_hash=document.content_hash,  # Preserve original hash
                metadata=chunk_metadata,
                embedding=None,  # Embedding will be generated later
            )
            chunked_docs.append(chunk_doc)

        return chunked_docs


def create_chunking_transformation(config: IngestionConfig) -> SentenceSplitter:
    """Create a LlamaIndex transformation object for chunking.

    This helper function creates a SentenceSplitter transformation
    that can be used directly in LlamaIndex IngestionPipeline.

    Args:
        config: Ingestion configuration with chunk_size and chunk_overlap

    Returns:
        SentenceSplitter transformation ready for IngestionPipeline

    Example:
        >>> from llamacrawl.config import get_config
        >>> config = get_config()
        >>> chunker = create_chunking_transformation(config.ingestion)
        >>> # Use in pipeline:
        >>> pipeline = IngestionPipeline(
        ...     transformations=[chunker, embed_model]
        ... )
    """
    return SentenceSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separator=" ",
    )
