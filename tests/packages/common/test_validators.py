"""Tests for URL validation utilities."""

import pytest

from packages.common.validators import URLValidationError, validate_url


class TestURLValidationError:
    """Test URLValidationError exception class."""

    def test_inherits_from_value_error(self) -> None:
        """URLValidationError should inherit from ValueError."""
        error = URLValidationError("test message")
        assert isinstance(error, ValueError)

    def test_stores_message(self) -> None:
        """URLValidationError should store the error message."""
        message = "Invalid URL format"
        error = URLValidationError(message)
        assert str(error) == message


class TestValidateURL:
    """Test validate_url function."""

    # Valid URLs
    def test_accepts_valid_https_url(self) -> None:
        """Should accept valid HTTPS URLs."""
        validate_url("https://example.com")
        validate_url("https://example.com/path")
        validate_url("https://example.com:8080/path?query=value")

    def test_accepts_valid_http_url(self) -> None:
        """Should accept valid HTTP URLs."""
        validate_url("http://public-site.com")
        validate_url("http://example.org/api/endpoint")

    def test_accepts_public_domain_names(self) -> None:
        """Should accept public domain names."""
        validate_url("https://google.com")
        validate_url("https://github.com")
        validate_url("https://api.openai.com")

    # Invalid schemes
    def test_rejects_file_scheme(self) -> None:
        """Should reject file:// URLs."""
        with pytest.raises(URLValidationError, match="Invalid URL scheme"):
            validate_url("file:///etc/passwd")

    def test_rejects_ftp_scheme(self) -> None:
        """Should reject ftp:// URLs."""
        with pytest.raises(URLValidationError, match="Invalid URL scheme"):
            validate_url("ftp://server.com")

    def test_rejects_data_scheme(self) -> None:
        """Should reject data:// URLs."""
        with pytest.raises(URLValidationError, match="Invalid URL scheme"):
            validate_url("data://text/plain;base64,SGVsbG8=")

    def test_rejects_javascript_scheme(self) -> None:
        """Should reject javascript:// URLs."""
        with pytest.raises(URLValidationError, match="Invalid URL scheme"):
            validate_url("javascript:alert(1)")

    def test_rejects_missing_scheme(self) -> None:
        """Should reject URLs without scheme."""
        with pytest.raises(URLValidationError, match="Invalid URL scheme"):
            validate_url("example.com")

    # Private IP addresses (SSRF protection)
    def test_rejects_localhost_ip(self) -> None:
        """Should reject 127.0.0.1 (localhost)."""
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://127.0.0.1")

    def test_rejects_localhost_range(self) -> None:
        """Should reject 127.0.0.0/8 range."""
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://127.0.0.5:8080")
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://127.255.255.255")

    def test_rejects_private_class_a(self) -> None:
        """Should reject 10.0.0.0/8 private range."""
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://10.0.0.1")
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://10.255.255.255")

    def test_rejects_private_class_b(self) -> None:
        """Should reject 172.16.0.0/12 private range."""
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://172.16.0.1")
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://172.31.255.255")

    def test_rejects_private_class_c(self) -> None:
        """Should reject 192.168.0.0/16 private range."""
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://192.168.1.1")
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://192.168.255.254")

    def test_rejects_link_local(self) -> None:
        """Should reject 169.254.0.0/16 link-local range."""
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://169.254.1.1")
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://169.254.255.254")

    # Internal hostnames
    def test_rejects_localhost_hostname(self) -> None:
        """Should reject 'localhost' hostname."""
        with pytest.raises(URLValidationError, match="internal hostname"):
            validate_url("http://localhost")
        with pytest.raises(URLValidationError, match="internal hostname"):
            validate_url("https://localhost:4207")

    def test_rejects_zero_address(self) -> None:
        """Should reject 0.0.0.0 address."""
        with pytest.raises(URLValidationError, match="internal hostname"):
            validate_url("http://0.0.0.0")

    def test_rejects_localhost_variants(self) -> None:
        """Should reject localhost case variants."""
        with pytest.raises(URLValidationError, match="internal hostname"):
            validate_url("http://LOCALHOST")
        with pytest.raises(URLValidationError, match="internal hostname"):
            validate_url("http://LocalHost")

    # Malformed URLs
    def test_rejects_malformed_url(self) -> None:
        """Should reject malformed URLs."""
        with pytest.raises(URLValidationError):
            validate_url("not a url")

    def test_rejects_url_with_spaces(self) -> None:
        """Should reject URLs with spaces."""
        with pytest.raises(URLValidationError):
            validate_url("ht tp://space.com")

    def test_rejects_empty_string(self) -> None:
        """Should reject empty string."""
        with pytest.raises(URLValidationError):
            validate_url("")

    def test_rejects_whitespace_only(self) -> None:
        """Should reject whitespace-only string."""
        with pytest.raises(URLValidationError):
            validate_url("   ")

    # Edge cases
    def test_rejects_ipv6_localhost(self) -> None:
        """Should reject IPv6 localhost (::1)."""
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://[::1]")

    def test_rejects_ipv6_link_local(self) -> None:
        """Should reject IPv6 link-local addresses."""
        with pytest.raises(URLValidationError, match="private or reserved IP"):
            validate_url("http://[fe80::1]")

    def test_accepts_public_ipv4(self) -> None:
        """Should accept public IPv4 addresses."""
        validate_url("http://8.8.8.8")  # Google DNS
        validate_url("http://1.1.1.1")  # Cloudflare DNS

    def test_accepts_public_ipv6(self) -> None:
        """Should accept public IPv6 addresses."""
        validate_url("http://[2001:4860:4860::8888]")  # Google DNS
