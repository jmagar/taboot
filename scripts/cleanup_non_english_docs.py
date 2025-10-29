#!/usr/bin/env python3
"""Remove non-English documents from Qdrant collection.

Usage:
    python scripts/cleanup_non_english_docs.py --dry-run      # Show what would be deleted
    python scripts/cleanup_non_english_docs.py --confirm      # Actually delete documents
"""

import argparse
import logging
from collections import Counter
from typing import Any

from qdrant_client import QdrantClient

from packages.common.config import get_config
from packages.common.language_detection import Language, detect_language

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main cleanup function."""
    parser = argparse.ArgumentParser(description="Cleanup non-English documents from Qdrant")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete non-English documents (DESTRUCTIVE)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed language detection results",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        parser.error("Must specify either --dry-run or --confirm")

    # Connect to Qdrant
    config = get_config()
    client = QdrantClient(url=config.qdrant_url)

    # Get collection name (hardcoded for now as it's not in config)
    collection_name = "taboot_docs"

    # Verify collection exists
    collections = client.get_collections()
    available_names = [c.name for c in collections.collections]
    if collection_name not in available_names:
        logger.error(f"Collection '{collection_name}' not found. Available: {available_names}")
        return

    logger.info(f"Analyzing collection: {collection_name}")

    # Fetch all documents
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=10000,  # Adjust if you have more documents
        with_payload=True,
        with_vectors=False,
    )

    logger.info(f"Fetched {len(points)} documents")

    # Analyze languages
    language_counts: Counter[Language] = Counter()
    non_english_ids: list[str | int] = []
    non_english_samples: dict[Language, list[tuple[str | int, str]]] = {}

    for point in points:
        # Access Record attributes directly
        payload: dict[str, Any] = point.payload or {}
        content = payload.get("content", "")

        if not isinstance(content, str):
            logger.warning(f"Skipping non-string content in point {point.id}")
            continue

        lang = detect_language(content)
        language_counts[lang] += 1

        if lang != Language.ENGLISH:
            non_english_ids.append(point.id)
            if lang not in non_english_samples:
                non_english_samples[lang] = []
            if len(non_english_samples[lang]) < 3:  # Keep 3 samples per language
                non_english_samples[lang].append((point.id, content[:100]))

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("LANGUAGE DISTRIBUTION:")
    logger.info("=" * 80)
    for lang, count in language_counts.most_common():
        percentage = (count / len(points)) * 100 if points else 0
        logger.info(f"  {lang.value:10s}: {count:4d} documents ({percentage:5.1f}%)")

    logger.info(f"\nTotal documents: {len(points)}")
    logger.info(f"English documents: {language_counts[Language.ENGLISH]}")
    logger.info(f"Non-English documents: {len(non_english_ids)}")

    if args.verbose and non_english_samples:
        logger.info("\n" + "=" * 80)
        logger.info("SAMPLE NON-ENGLISH CONTENT:")
        logger.info("=" * 80)
        for lang, samples in non_english_samples.items():
            logger.info(f"\n{lang.value} samples:")
            for point_id, text in samples:
                logger.info(f"  ID: {point_id}")
                logger.info(f"  Text: {text}...\n")

    # Delete if confirmed
    if len(non_english_ids) > 0:
        if args.dry_run:
            logger.info(
                f"\n[DRY RUN] Would delete {len(non_english_ids)} non-English documents"
            )
        else:
            logger.info(f"\nDeleting {len(non_english_ids)} non-English documents...")
            client.delete(
                collection_name=collection_name,
                points_selector=non_english_ids,
            )
            logger.info("✓ Deletion complete")

            # Verify
            info = client.get_collection(collection_name)
            logger.info(f"✓ Collection now has {info.points_count} documents")
    else:
        logger.info("\n✓ No non-English documents found")


if __name__ == "__main__":
    main()
