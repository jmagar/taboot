"""URL validation utilities with SSRF protection."""

import ipaddress
import socket
from urllib.parse import urlparse


class URLValidationError(ValueError):
    """Exception raised when URL validation fails."""

    pass


def validate_url(url: str) -> None:
    """
    Validate URL for security and correctness.

    Only allows http/https schemes and blocks access to private IP ranges
    and internal hostnames to prevent SSRF attacks.

    Args:
        url: URL string to validate

    Raises:
        URLValidationError: If URL is invalid, uses disallowed scheme,
            or points to private/internal address

    Examples:
        >>> validate_url("https://example.com")  # OK
        >>> validate_url("http://127.0.0.1")  # raises URLValidationError
        >>> validate_url("file:///etc/passwd")  # raises URLValidationError
    """
    # Reject empty or whitespace-only strings
    if not url or not url.strip():
        raise URLValidationError("URL cannot be empty")

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise URLValidationError(f"Malformed URL: {e}") from e

    # Validate scheme
    if parsed.scheme not in ("http", "https"):
        raise URLValidationError(
            f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed."
        )

    # Extract hostname
    hostname = parsed.hostname
    if not hostname:
        raise URLValidationError("URL must have a hostname")

    # Block internal hostnames
    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "0.0.0.0"):
        raise URLValidationError(f"Access to internal hostname '{hostname}' is blocked")

    # Check if hostname is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP address, it's a hostname - need to resolve it
        try:
            # Resolve hostname to IP and check if it's private
            addr_info = socket.getaddrinfo(hostname, None)
            for _family, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                        raise URLValidationError(
                            f"Hostname '{hostname}' resolves to private or reserved IP '{ip_str}'"
                        )
                except ValueError:
                    # Skip if IP parsing fails
                    continue
        except socket.gaierror:
            # DNS resolution failed - we'll allow this since it might be a valid
            # domain that's temporarily unreachable, and the actual request will fail anyway
            pass
    else:
        # It is an IP address - block private, loopback, link-local, and reserved IPs
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise URLValidationError(
                f"Access to private or reserved IP address '{hostname}' is blocked"
            )
