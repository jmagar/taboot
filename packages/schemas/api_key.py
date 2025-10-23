"""API key schema for authentication."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ApiKey(BaseModel):
    """API key model for authentication.

    Attributes:
        key_id: Unique key identifier (e.g., 'key_abc123').
        key_hash: SHA-256 hash of the actual key.
        name: Human-readable key name.
        created_at: Key creation timestamp.
        last_used_at: Last usage timestamp (nullable).
        rate_limit_rpm: Requests per minute limit.
        is_active: Whether key is active.
    """

    key_id: str = Field(..., min_length=1, max_length=128)
    key_hash: str = Field(..., min_length=64, max_length=64)
    name: str = Field(..., min_length=1, max_length=256)
    created_at: datetime
    last_used_at: datetime | None = None
    rate_limit_rpm: int = Field(..., ge=1, le=10000)
    is_active: bool = True

    @field_validator("key_hash")
    @classmethod
    def validate_key_hash_hex(cls, v: str) -> str:
        """Validate that key_hash is 64 hexadecimal characters.

        Args:
            v: The key hash value.

        Returns:
            str: The validated key hash.

        Raises:
            ValueError: If key_hash is not valid.
        """
        if len(v) != 64:
            raise ValueError("key_hash must be exactly 64 characters")
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("key_hash must be 64 hexadecimal characters")
        return v.lower()


__all__ = ["ApiKey"]
