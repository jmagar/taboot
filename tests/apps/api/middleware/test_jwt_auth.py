"""Tests for JWT authentication middleware AUTH_SECRET validation.

Tests ensure that weak AUTH_SECRET values are rejected at startup,
preventing brute-force attacks on JWT tokens.
"""

from __future__ import annotations

import secrets

import pytest

from apps.api.middleware.jwt_auth import MIN_SECRET_LENGTH, _get_auth_secret


class TestAuthSecretValidation:
    """Test AUTH_SECRET validation logic."""

    def test_missing_auth_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure missing AUTH_SECRET is rejected with helpful error message."""
        monkeypatch.delenv("AUTH_SECRET", raising=False)
        _get_auth_secret.cache_clear()

        with pytest.raises(
            RuntimeError,
            match=r"AUTH_SECRET environment variable must be set.*secrets\.token_urlsafe",
        ):
            _get_auth_secret()

    def test_empty_auth_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure empty AUTH_SECRET is rejected."""
        monkeypatch.setenv("AUTH_SECRET", "")
        _get_auth_secret.cache_clear()

        with pytest.raises(
            RuntimeError,
            match=r"AUTH_SECRET environment variable must be set.*secrets\.token_urlsafe",
        ):
            _get_auth_secret()

    def test_short_auth_secret_5_chars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure very short AUTH_SECRET is rejected (5 characters)."""
        monkeypatch.setenv("AUTH_SECRET", "short")
        _get_auth_secret.cache_clear()

        with pytest.raises(
            RuntimeError,
            match=(
                rf"AUTH_SECRET must be at least {MIN_SECRET_LENGTH} characters.*"
                r"Current length: 5"
            ),
        ):
            _get_auth_secret()

    def test_short_auth_secret_31_chars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure AUTH_SECRET just below minimum length is rejected (31 characters)."""
        # 31 characters - just 1 short of minimum
        monkeypatch.setenv("AUTH_SECRET", "a" * 31)
        _get_auth_secret.cache_clear()

        with pytest.raises(
            RuntimeError,
            match=(
                rf"AUTH_SECRET must be at least {MIN_SECRET_LENGTH} characters.*"
                r"Current length: 31"
            ),
        ):
            _get_auth_secret()

    def test_weak_auth_secret_common_passwords(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure common weak passwords are rejected even if long enough."""
        weak_secrets = [
            "password" * 4,  # 32 chars but all same pattern
            "test1234" * 4,  # 32 chars but repetitive
            "a" * 32,  # All same character
            "1" * 32,  # All same digit
        ]

        for weak_secret in weak_secrets:
            monkeypatch.setenv("AUTH_SECRET", weak_secret)
            _get_auth_secret.cache_clear()

            with pytest.raises(
                RuntimeError,
                match=r"AUTH_SECRET has insufficient entropy.*too many repeated characters",
            ):
                _get_auth_secret()

    def test_low_entropy_auth_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure low-entropy secrets are rejected (entropy check)."""
        # 32 characters but only 10 unique characters (< MIN_SECRET_LENGTH // 2)
        low_entropy_secret = "abcdefghij" * 3 + "ab"  # 32 chars, 10 unique
        monkeypatch.setenv("AUTH_SECRET", low_entropy_secret)
        _get_auth_secret.cache_clear()

        with pytest.raises(
            RuntimeError,
            match=r"AUTH_SECRET has insufficient entropy.*too many repeated characters",
        ):
            _get_auth_secret()

    def test_strong_auth_secret_32_chars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure strong 32-character secret is accepted."""
        strong_secret = secrets.token_urlsafe(32)
        monkeypatch.setenv("AUTH_SECRET", strong_secret)
        _get_auth_secret.cache_clear()

        result = _get_auth_secret()
        assert result == strong_secret
        assert len(result) >= MIN_SECRET_LENGTH

    def test_strong_auth_secret_64_chars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure strong 64-character secret is accepted."""
        strong_secret = secrets.token_urlsafe(64)
        monkeypatch.setenv("AUTH_SECRET", strong_secret)
        _get_auth_secret.cache_clear()

        result = _get_auth_secret()
        assert result == strong_secret
        assert len(result) >= MIN_SECRET_LENGTH

    def test_auth_secret_caching(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure AUTH_SECRET is cached after first validation."""
        strong_secret = secrets.token_urlsafe(32)
        monkeypatch.setenv("AUTH_SECRET", strong_secret)
        _get_auth_secret.cache_clear()

        # First call validates and caches
        result1 = _get_auth_secret()

        # Change env var (should not affect cached value)
        monkeypatch.setenv("AUTH_SECRET", "different_value")

        # Second call returns cached value
        result2 = _get_auth_secret()

        assert result1 == result2 == strong_secret

    def test_auth_secret_validation_message_includes_generation_command(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ensure error messages include secret generation command."""
        monkeypatch.setenv("AUTH_SECRET", "short")
        _get_auth_secret.cache_clear()

        with pytest.raises(
            RuntimeError,
            match=r"python -c 'import secrets; print\(secrets\.token_urlsafe\(32\)\)'",
        ):
            _get_auth_secret()

    def test_auth_secret_minimum_length_constant(self) -> None:
        """Verify MIN_SECRET_LENGTH is set correctly for HS256 (256 bits = 32 bytes)."""
        assert MIN_SECRET_LENGTH == 32


class TestAuthSecretEdgeCases:
    """Test edge cases for AUTH_SECRET validation."""

    def test_auth_secret_with_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure secrets with leading/trailing whitespace are validated as-is."""
        # Secret with spaces - should still meet length requirement
        secret_with_spaces = " " + secrets.token_urlsafe(32) + " "
        monkeypatch.setenv("AUTH_SECRET", secret_with_spaces)
        _get_auth_secret.cache_clear()

        result = _get_auth_secret()
        assert result == secret_with_spaces
        assert len(result) >= MIN_SECRET_LENGTH

    def test_auth_secret_special_characters(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure secrets with special characters are accepted."""
        # secrets.token_urlsafe produces URL-safe base64 (letters, digits, -, _)
        # This test ensures we don't accidentally reject valid characters
        strong_secret = secrets.token_urlsafe(32)
        monkeypatch.setenv("AUTH_SECRET", strong_secret)
        _get_auth_secret.cache_clear()

        result = _get_auth_secret()
        assert result == strong_secret

    def test_auth_secret_unicode_characters(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure secrets with unicode characters are handled correctly."""
        # While not recommended, unicode should be handled gracefully
        unicode_secret = "🔒" * 32  # 32 emoji characters
        monkeypatch.setenv("AUTH_SECRET", unicode_secret)
        _get_auth_secret.cache_clear()

        # This should be rejected due to low entropy (all same character)
        with pytest.raises(
            RuntimeError,
            match=r"AUTH_SECRET has insufficient entropy",
        ):
            _get_auth_secret()

    def test_auth_secret_exactly_minimum_length(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure exactly 32-character secret with good entropy is accepted."""
        # Generate exactly 32 bytes of random data
        strong_secret = secrets.token_urlsafe(24)  # 24 bytes -> 32 chars in base64
        assert len(strong_secret) == 32
        monkeypatch.setenv("AUTH_SECRET", strong_secret)
        _get_auth_secret.cache_clear()

        result = _get_auth_secret()
        assert result == strong_secret
        assert len(result) == MIN_SECRET_LENGTH
