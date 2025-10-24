"""Document chunker using LlamaIndex SentenceSplitter.

Implements semantic chunking with configurable size and overlap.
Per research.md: Use LlamaIndex SentenceSplitter with 256-512 tokens, 10% overlap.
"""

import logging

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter

logger = logging.getLogger(__name__)


class Chunker:
    """Document chunker using LlamaIndex SentenceSplitter.

    Splits documents into semantic chunks with configurable size and overlap.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 51,
        separator: str = " ",
    ) -> None:
        """Initialize chunker with size and overlap parameters.

        Args:
            chunk_size: Maximum tokens per chunk (default: 512).
            chunk_overlap: Overlap tokens between chunks (default: 51, ~10%).
            separator: Separator for splitting (default: space).
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

        # Initialize LlamaIndex SentenceSplitter
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=separator,
        )

        logger.info(
            f"Initialized Chunker (chunk_size={chunk_size}, "
            f"chunk_overlap={chunk_overlap}, separator='{separator}')"
        )

    def chunk_document(self, doc: Document) -> list[Document]:
        """Chunk a document into smaller semantic chunks.

        Args:
            doc: LlamaIndex Document to chunk.

        Returns:
            list[Document]: List of chunked Document objects with preserved metadata.
        """
        if not doc.text or doc.text.strip() == "":
            logger.debug("Empty document, returning empty chunk list")
            return []

        logger.debug(f"Chunking document: {len(doc.text)} chars")

        # Split using LlamaIndex SentenceSplitter
        nodes = self.splitter.get_nodes_from_documents([doc])

        # Convert nodes back to Documents and preserve metadata
        chunks: list[Document] = []
        for i, node in enumerate(nodes):
            chunk_metadata = doc.metadata.copy() if doc.metadata else {}
            chunk_metadata["chunk_index"] = i
            chunk_metadata["chunk_count"] = len(nodes)

            chunk = Document(
                text=node.get_content(),
                metadata=chunk_metadata,
            )
            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from document")

        return chunks
