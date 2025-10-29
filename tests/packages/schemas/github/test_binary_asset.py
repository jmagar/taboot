"""Tests for BinaryAsset entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Size validation
- URL validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.binary_asset import BinaryAsset


class TestBinaryAssetEntity:
    """Test suite for BinaryAsset entity."""

    def test_binary_asset_minimal_valid(self) -> None:
        """Test BinaryAsset with only required fields."""
        now = datetime.now(UTC)
        asset = BinaryAsset(
            file_path="releases/app-v1.0.0.tar.gz",
            size=1024000,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert asset.file_path == "releases/app-v1.0.0.tar.gz"
        assert asset.size == 1024000
        assert asset.mime_type is None
        assert asset.download_url is None

    def test_binary_asset_full_valid(self) -> None:
        """Test BinaryAsset with all fields populated."""
        now = datetime.now(UTC)
        asset = BinaryAsset(
            file_path="releases/app-v1.0.0.tar.gz",
            size=1024000,
            mime_type="application/gzip",
            download_url="https://github.com/owner/repo/releases/download/v1.0.0/app-v1.0.0.tar.gz",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert asset.mime_type == "application/gzip"
        assert asset.download_url == "https://github.com/owner/repo/releases/download/v1.0.0/app-v1.0.0.tar.gz"

    def test_binary_asset_missing_required_size(self) -> None:
        """Test BinaryAsset validation fails without size."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BinaryAsset(
                file_path="test.bin",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("size",) for e in errors)

    def test_binary_asset_negative_size(self) -> None:
        """Test BinaryAsset validation fails with negative size."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            BinaryAsset(
                file_path="test.bin",
                size=-1,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("size",) for e in errors)
