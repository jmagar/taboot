"""Tailscale network topology reader for Taboot platform.

Fetches device information from Tailscale API and extracts:
- Host nodes (hostname)
- IP nodes (addresses with type detection)
- LOCATED_AT relationships (host -> IP)

Per data-model.md: Extracts structured network topology to nodes/edges deterministically.

API Reference:
    https://tailscale.com/kb/1101/api/#get-tailnet-devices
"""

import ipaddress
import logging
from typing import Any, Final

import requests

logger = logging.getLogger(__name__)

# Tailscale API configuration
TAILSCALE_API_BASE_URL: Final[str] = "https://api.tailscale.com/api/v2"
API_TIMEOUT_SECONDS: Final[int] = 30


class TailscaleError(Exception):
    """Base exception for TailscaleReader errors."""

    pass


class TailscaleAPIError(TailscaleError):
    """Raised when Tailscale API request fails.

    This includes authentication failures, network errors, rate limiting,
    and invalid API responses.
    """

    pass


class InvalidIPError(TailscaleError):
    """Raised when IP address format is invalid.

    Triggered when parsing IP addresses that don't conform to valid
    IPv4 or IPv6 formats.
    """

    pass


class TailscaleReader:
    """Tailscale API reader for network topology extraction.

    Fetches device list from Tailscale API and extracts Host nodes, IP nodes,
    and LOCATED_AT relationships linking hosts to their IP addresses.

    The reader connects to the Tailscale API v2 to retrieve all devices in a
    tailnet, extracting network topology information for graph storage in Neo4j.

    Tailscale assigns IP addresses from:
    - IPv4: 100.64.0.0/10 (CGNAT range)
    - IPv6: fd7a:115c:a1e0::/48

    All extracted IPs are marked as "static" allocation since Tailscale manages
    them persistently per device.

    Example:
        >>> reader = TailscaleReader(api_key="tskey-...", tailnet="example.com")
        >>> data = reader.load_data()
        >>> print(f"Found {len(data['hosts'])} hosts")
    """

    def __init__(self, api_key: str, tailnet: str) -> None:
        """Initialize TailscaleReader with API credentials.

        Args:
            api_key: Tailscale API key for authentication. Generate from:
                     https://login.tailscale.com/admin/settings/keys
            tailnet: Tailscale tailnet name. This can be:
                     - Organization domain (e.g., "example.com")
                     - User email (e.g., "user@example.com")
                     - Tailnet ID

        Raises:
            ValueError: If api_key or tailnet is empty.

        Example:
            >>> reader = TailscaleReader(
            ...     api_key="tskey-api-...",
            ...     tailnet="example.com"
            ... )
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if not tailnet:
            raise ValueError("tailnet cannot be empty")

        self.api_key: str = api_key
        self.tailnet: str = tailnet
        self.api_base_url: str = TAILSCALE_API_BASE_URL

        logger.info(f"Initialized TailscaleReader (tailnet={tailnet})")

    def load_data(self) -> dict[str, Any]:
        """Load device data from Tailscale API and extract topology.

        Returns:
            dict[str, Any]: Structured data with hosts, IPs, and relationships.
                {
                    "hosts": [
                        {
                            "hostname": str,
                        },
                        ...
                    ],
                    "ips": [
                        {
                            "addr": str,
                            "ip_type": "v4" | "v6",
                            "allocation": "static",
                        },
                        ...
                    ],
                    "relationships": [
                        {
                            "type": "LOCATED_AT",
                            "source": str,  # hostname
                            "target": str,  # IP address
                        },
                        ...
                    ]
                }

        Raises:
            TailscaleAPIError: If API request fails.
            InvalidIPError: If IP address format is invalid.
        """
        logger.info(f"Loading data from Tailscale API for tailnet {self.tailnet}")

        # Fetch devices from API
        devices = self._fetch_devices()

        hosts: list[dict[str, Any]] = []
        ips: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []

        # Track unique IP addresses to avoid duplicates
        seen_ips: set[str] = set()

        for device in devices:
            hostname = device.get("hostname", "")
            if not hostname:
                logger.warning(f"Skipping device without hostname: {device.get('id')}")
                continue

            # Extract host node
            hosts.append({"hostname": hostname})

            # Extract IP addresses
            addresses = device.get("addresses", [])
            for addr in addresses:
                # Validate and classify IP address
                ip_info = self._parse_ip_address(addr)

                # Add IP node if not already seen
                if addr not in seen_ips:
                    ips.append(ip_info)
                    seen_ips.add(addr)

                # Create LOCATED_AT relationship
                relationships.append(
                    {
                        "type": "LOCATED_AT",
                        "source": hostname,
                        "target": addr,
                    }
                )

        logger.info(
            f"Extracted {len(hosts)} hosts, {len(ips)} IPs, {len(relationships)} relationships"
        )

        return {
            "hosts": hosts,
            "ips": ips,
            "relationships": relationships,
        }

    def _fetch_devices(self) -> list[dict[str, Any]]:
        """Fetch device list from Tailscale API.

        Makes a GET request to the Tailscale API to retrieve all devices in the
        tailnet. Handles authentication via Bearer token.

        API Response Format:
            {
                "devices": [
                    {
                        "id": "device_id",
                        "hostname": "server01",
                        "addresses": ["100.64.1.10", "fd7a:115c:a1e0::1"],
                        "os": "linux",
                        "name": "server01.example.com",
                        ...
                    },
                    ...
                ]
            }

        Returns:
            list[dict[str, Any]]: List of device objects from API. Each device
                                  contains id, hostname, addresses, os, and name.

        Raises:
            TailscaleAPIError: If API request fails due to:
                - Authentication failure (401)
                - Network errors (connection timeout, DNS failure)
                - Rate limiting (429)
                - Invalid API response
        """
        url = f"{self.api_base_url}/tailnet/{self.tailnet}/devices"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            logger.debug(f"Fetching devices from {url}")
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()

            devices = data.get("devices", [])
            logger.info(f"Fetched {len(devices)} devices from Tailscale API")
            return devices

        except requests.exceptions.HTTPError as e:
            # Handle specific HTTP errors
            status_code = e.response.status_code if e.response else None
            if status_code == 401:
                logger.error("Authentication failed - invalid API key")
                raise TailscaleAPIError("Authentication failed - invalid API key") from e
            elif status_code == 429:
                logger.error("Rate limit exceeded")
                raise TailscaleAPIError("Rate limit exceeded") from e
            else:
                logger.error(f"HTTP error fetching devices: {e}")
                raise TailscaleAPIError(f"HTTP error fetching devices: {e}") from e

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout after {API_TIMEOUT_SECONDS}s")
            raise TailscaleAPIError(f"Request timeout after {API_TIMEOUT_SECONDS}s") from e

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching devices: {e}")
            raise TailscaleAPIError(f"Network error fetching devices: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error fetching devices: {e}")
            raise TailscaleAPIError(f"Failed to fetch devices from Tailscale API: {e}") from e

    def _parse_ip_address(self, addr: str) -> dict[str, Any]:
        """Parse and validate IP address, determine type (v4/v6).

        Uses Python's ipaddress module to validate and classify IP addresses.
        All Tailscale IPs are marked as "static" since Tailscale manages them
        persistently and they don't change unless manually reassigned.

        Args:
            addr: IP address string in dotted notation.
                  Examples: "100.64.1.10", "fd7a:115c:a1e0::1"

        Returns:
            dict[str, Any]: IP node data with:
                - addr: str - The IP address
                - ip_type: "v4" | "v6" - IP version
                - allocation: "static" - Always static for Tailscale

        Raises:
            InvalidIPError: If IP address format is invalid or cannot be parsed.
                           This includes malformed addresses like "999.999.999.999"
                           or incomplete addresses.

        Example:
            >>> reader._parse_ip_address("100.64.1.10")
            {'addr': '100.64.1.10', 'ip_type': 'v4', 'allocation': 'static'}
        """
        try:
            ip_obj = ipaddress.ip_address(addr)

            # Determine IP type
            if isinstance(ip_obj, ipaddress.IPv4Address):
                ip_type = "v4"
            elif isinstance(ip_obj, ipaddress.IPv6Address):
                ip_type = "v6"
            else:
                # Should never reach here due to ipaddress.ip_address() validation
                raise InvalidIPError(f"Unknown IP address type: {addr}")

            # Tailscale assigns static IPs from:
            # - IPv4: 100.64.0.0/10 (CGNAT range)
            # - IPv6: fd7a:115c:a1e0::/48
            # These are persistent per device, not dynamically assigned
            allocation = "static"

            return {
                "addr": addr,
                "ip_type": ip_type,
                "allocation": allocation,
            }

        except ValueError as e:
            logger.error(f"Invalid IP address format: {addr}")
            raise InvalidIPError(f"Invalid IP address: {addr}") from e
