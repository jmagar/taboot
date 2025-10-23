"""Tests for API key schema models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.api_key import ApiKey


def test_api_key_creation():
    """Test creating API key model."""
    now = datetime.now(UTC)
    api_key = ApiKey(
        key_id="key_123abc",
        key_hash="abcdef1234567890" * 4,  # 64 hex chars
        name="Test API Key",
        created_at=now,
        last_used_at=None,
        rate_limit_rpm=60,
        is_active=True,
    )

    assert api_key.key_id == "key_123abc"
    assert len(api_key.key_hash) == 64
    assert api_key.rate_limit_rpm == 60
    assert api_key.is_active is True


def test_api_key_hash_validation():
    """Test that key_hash must be 64 hex chars."""
    # Test with non-hex characters (64 chars but not hex)
    with pytest.raises(ValidationError, match="key_hash must be 64 hexadecimal"):
        ApiKey(
            key_id="key_123",
            key_hash="z" * 64,  # 64 chars but not hexadecimal
            name="Test",
            created_at=datetime.now(UTC),
            last_used_at=None,
            rate_limit_rpm=60,
            is_active=True,
        )
