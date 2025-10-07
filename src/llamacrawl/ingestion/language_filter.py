"""Language filtering transformation for ingestion pipeline.

This module provides the LanguageFilter transformation component that detects
and filters document chunks by language BEFORE embedding. This saves compute
costs and storage space by preventing non-target language content from being
embedded and stored.

The filter uses fast-langdetect for accurate and efficient language detection
(95%+ accuracy, 80x faster than alternatives).
"""

from collections import Counter
from collections.abc import Sequence
from typing import Any

from fast_langdetect import detect
from llama_index.core.schema import BaseNode, TextNode, TransformComponent
from pydantic import Field

from llamacrawl.models.document import Document
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)

# Valid ISO 639-1 language codes (subset of most common)
VALID_LANGUAGE_CODES = {
    "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
    "ar", "hi", "nl", "pl", "tr", "vi", "th", "sv", "da", "fi",
    "no", "cs", "ro", "hu", "el", "he", "id", "ms", "uk", "bg",
}


class LanguageFilter(TransformComponent):
    """Filter document chunks by detected language.

    This transformation detects the language of each text chunk and filters
    out chunks that don't match the allowed languages. Filtering happens
    BEFORE embedding to save compute costs and storage space.

    Uses fast-langdetect for detection (95%+ accuracy, offline operation).

    Attributes:
        allowed_languages: Set of ISO 639-1 language codes to keep (e.g., {"en"})
        confidence_threshold: Minimum detection confidence (0.0-1.0)
        min_content_length: Minimum text length for detection (skip shorter text)
        log_filtered: Whether to log detailed filtering statistics

    Example:
        >>> filter = LanguageFilter(allowed_languages={"en"}, confidence_threshold=0.8)
        >>> nodes = [TextNode(text="English text"), TextNode(text="French text")]
        >>> filtered_nodes = filter(nodes)
        >>> len(filtered_nodes)  # Only English node remains
        1
    """

    # Pydantic fields with defaults for LlamaIndex TransformComponent
    allowed_languages: set[str] = Field(default_factory=set, description="Set of ISO 639-1 language codes to keep")
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum detection confidence")
    min_content_length: int = Field(default=50, ge=0, description="Minimum text length for detection")
    log_filtered: bool = Field(default=True, description="Log filtering statistics")

    def __init__(
        self,
        allowed_languages: set[str] | None = None,
        confidence_threshold: float = 0.8,
        min_content_length: int = 50,
        log_filtered: bool = True,
        **kwargs: Any,
    ):
        """Initialize language filter.

        Args:
            allowed_languages: Set of ISO 639-1 codes to keep. If empty/None, allows all.
            confidence_threshold: Minimum detection confidence (0.0-1.0). Default: 0.8
            min_content_length: Skip detection for text shorter than this. Default: 50
            log_filtered: Log filtering statistics. Default: True
            **kwargs: Additional arguments for parent class

        Raises:
            ValueError: If confidence_threshold is out of range or language codes invalid
        """
        # Normalize and validate language codes
        if allowed_languages:
            normalized_langs = {lang.lower() for lang in allowed_languages}
            invalid_langs = normalized_langs - VALID_LANGUAGE_CODES
            if invalid_langs:
                logger.warning(
                    f"Unrecognized language codes (may not be supported): {invalid_langs}",
                    extra={"invalid_codes": list(invalid_langs)},
                )
            allowed_languages = normalized_langs
        else:
            allowed_languages = set()

        # Initialize parent with validated fields
        super().__init__(
            allowed_languages=allowed_languages,
            confidence_threshold=confidence_threshold,
            min_content_length=min_content_length,
            log_filtered=log_filtered,
            **kwargs,
        )

        logger.info(
            "LanguageFilter initialized",
            extra={
                "allowed_languages": list(self.allowed_languages) if self.allowed_languages else "all",
                "confidence_threshold": self.confidence_threshold,
                "min_content_length": self.min_content_length,
            },
        )

    def __call__(
        self,
        nodes: Sequence[BaseNode],
        **kwargs: Any,
    ) -> list[BaseNode]:
        """Filter nodes by detected language.

        Args:
            nodes: Sequence of document nodes/chunks to filter
            **kwargs: Additional parameters (unused)

        Returns:
            Filtered list of nodes that match allowed languages

        Note:
            - Short text (< min_content_length) passes through without detection
            - Detection errors result in node being included (fail open)
            - Only first 1000 chars are used for detection (efficiency)
        """
        if not nodes:
            return []

        # If no language restrictions, pass through
        if not self.allowed_languages:
            logger.debug("No language restrictions configured, passing all nodes through")
            return list(nodes)

        filtered_nodes: list[BaseNode] = []
        filtered_count = 0
        detected_languages: Counter[str] = Counter()
        low_confidence_count = 0
        error_count = 0

        for node in nodes:
            # Extract text content
            text = node.get_content(metadata_mode="none")

            # Skip detection for short text (likely not enough content for accuracy)
            if len(text) < self.min_content_length:
                filtered_nodes.append(node)
                continue

            try:
                # Detect language on first 1000 chars for efficiency
                # fast-langdetect is fast, but no need to process very long text
                detection_text = text[:1000]
                result = detect(detection_text)
                if isinstance(result, list):
                    detection_result: dict[str, Any] = result[0] if result else {}
                elif isinstance(result, dict):
                    detection_result = result
                else:
                    detection_result = {}

                detected_lang = str(detection_result.get("lang", "")).lower()
                confidence_value = detection_result.get("score", 0.0)
                confidence = (
                    float(confidence_value)
                    if isinstance(confidence_value, (int, float))
                    else 0.0
                )

                if detected_lang:
                    detected_languages[detected_lang] += 1

                # Check if language is allowed
                if detected_lang in self.allowed_languages:
                    # Check confidence threshold
                    if confidence >= self.confidence_threshold:
                        filtered_nodes.append(node)
                    else:
                        # Low confidence - include node (fail open)
                        low_confidence_count += 1
                        filtered_nodes.append(node)
                        logger.debug(
                            f"Low confidence detection ({confidence:.2f}), including node",
                            extra={
                                "detected_lang": detected_lang,
                                "confidence": confidence,
                                "threshold": self.confidence_threshold,
                            },
                        )
                else:
                    # Language not in allowlist - filter out
                    filtered_count += 1
                    logger.debug(
                        f"Filtered node with language {detected_lang} (confidence: {confidence:.2f})",
                        extra={
                            "detected_lang": detected_lang,
                            "confidence": confidence,
                            "text_preview": text[:100] + "...",
                        },
                    )

            except Exception as e:
                # Detection error - include node (fail open)
                error_count += 1
                filtered_nodes.append(node)
                logger.debug(
                    f"Language detection failed, including node: {e}",
                    extra={"error": str(e), "text_preview": text[:100] + "..."},
                )

        # Log summary statistics
        if self.log_filtered:
            filter_rate = (filtered_count / len(nodes) * 100) if nodes else 0.0
            kept_count = len(filtered_nodes)

            logger.info(
                f"Language filtering complete: kept {kept_count}/{len(nodes)} nodes ({filter_rate:.1f}% filtered)",
                extra={
                    "total_nodes": len(nodes),
                    "kept_nodes": kept_count,
                    "filtered_nodes": filtered_count,
                    "filter_rate_pct": round(filter_rate, 1),
                    "detected_languages": dict(detected_languages.most_common(10)),
                    "low_confidence_count": low_confidence_count,
                    "error_count": error_count,
                },
            )

        return filtered_nodes


def build_language_filter_from_config(
    config: Any | None,
    *,
    log_filtered_override: bool | None = None,
) -> LanguageFilter | None:
    """Create a LanguageFilter instance from ingestion configuration.

    Args:
        config: Language filter configuration object (must expose attributes:
            enabled, allowed_languages, confidence_threshold, min_content_length,
            and log_filtered). None returns None.
        log_filtered_override: Optional override for log_filtered behavior.

    Returns:
        Configured LanguageFilter instance or None if disabled.
    """
    if config is None:
        return None

    enabled = getattr(config, "enabled", False)
    if not enabled:
        logger.debug("Language filter disabled via configuration; skipping creation")
        return None

    allowed_languages = {
        str(lang).lower()
        for lang in getattr(config, "allowed_languages", [])
        if str(lang).strip()
    }

    confidence_threshold = float(getattr(config, "confidence_threshold", 0.8))
    min_content_length = int(getattr(config, "min_content_length", 50))
    log_filtered = (
        bool(getattr(config, "log_filtered", True))
        if log_filtered_override is None
        else log_filtered_override
    )

    return LanguageFilter(
        allowed_languages=allowed_languages,
        confidence_threshold=confidence_threshold,
        min_content_length=min_content_length,
        log_filtered=log_filtered,
    )


def filter_documents_by_language(
    documents: Sequence[Document],
    language_filter: LanguageFilter | None,
) -> list[Document]:
    """Filter LlamaCrawl Document objects using LanguageFilter.

    Args:
        documents: Documents to filter.
        language_filter: Configured LanguageFilter instance. If None, returns
            documents unchanged.

    Returns:
        Filtered list of Document objects preserving original order.
    """
    if not documents:
        return []

    if language_filter is None or not language_filter.allowed_languages:
        # Nothing to filter; return shallow copy to avoid accidental mutation.
        return list(documents)

    # Convert documents to TextNodes for reuse of LanguageFilter logic.
    nodes: list[TextNode] = [
        TextNode(
            text=document.content,
            id_=document.doc_id,
            metadata={"doc_id": document.doc_id},
        )
        for document in documents
    ]

    filtered_nodes = language_filter(nodes)
    kept_doc_ids = {node.node_id for node in filtered_nodes}

    if not kept_doc_ids:
        return []

    return [document for document in documents if document.doc_id in kept_doc_ids]


# Export public API
__all__ = [
    "LanguageFilter",
    "build_language_filter_from_config",
    "filter_documents_by_language",
]
