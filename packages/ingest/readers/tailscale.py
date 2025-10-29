"""Tailscale network topology reader for Taboot platform.

Fetches device information from Tailscale API and extracts:
- TailscaleDevice entities (new schema format)
- TailscaleNetwork entities (extracted from subnet routes)
- TailscaleACL entities (placeholder for future implementation)
- Legacy format: Host nodes, IP nodes, LOCATED_AT relationships

Per data-model.md: Extracts structured network topology to nodes/edges deterministically.

API Reference:
    https://tailscale.com/kb/1101/api/#get-tailnet-devices
"""

import ipaddress
import logging
from datetime import UTC, datetime
from typing import Any, Final

import requests

from packages.schemas.tailscale import TailscaleACL, TailscaleDevice, TailscaleNetwork

logger = logging.getLogger(__name__)

# Extractor version for temporal tracking
EXTRACTOR_VERSION: Final[str] = "1.0.0"

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
            dict[str, Any]: Structured data with new entity types and legacy format.
                {
                    # New format (Phase 4)
                    "devices": [TailscaleDevice, ...],
                    "networks": [TailscaleNetwork, ...],
                    "acls": [TailscaleACL, ...],

                    # Legacy format (backward compatibility)
                    "hosts": [{"hostname": str}, ...],
                    "ips": [{"addr": str, "ip_type": "v4"|"v6", "allocation": "static"}, ...],
                    "relationships": [{"type": "LOCATED_AT", "source": str, "target": str}, ...]
                }

        Raises:
            TailscaleAPIError: If API request fails.
            InvalidIPError: If IP address format is invalid.
        """
        logger.info(f"Loading data from Tailscale API for tailnet {self.tailnet}")

        # Fetch devices from API
        devices_raw = self._fetch_devices()

        # Initialize result containers
        devices: list[TailscaleDevice] = []
        networks: list[TailscaleNetwork] = []
        acls: list[TailscaleACL] = []

        # Legacy format containers
        hosts: list[dict[str, Any]] = []
        ips: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []

        # Track unique IPs and networks to avoid duplicates
        seen_ips: set[str] = set()
        seen_networks: set[str] = set()

        # Current timestamp for extraction metadata
        now = datetime.now(UTC)

        for device_raw in devices_raw:
            hostname = device_raw.get("hostname", "")
            if not hostname:
                logger.warning(f"Skipping device without hostname: {device_raw.get('id')}")
                continue

            # Extract TailscaleDevice entity
            device_entity = self._extract_device_entity(device_raw, now)
            devices.append(device_entity)

            # Extract legacy host node
            hosts.append({"hostname": hostname})

            # Extract IP addresses
            addresses = device_raw.get("addresses", [])
            for addr in addresses:
                # Validate and classify IP address
                ip_info = self._parse_ip_address(addr)

                # Add IP node if not already seen (legacy format)
                if addr not in seen_ips:
                    ips.append(ip_info)
                    seen_ips.add(addr)

                # Create LOCATED_AT relationship (legacy format)
                relationships.append(
                    {
                        "type": "LOCATED_AT",
                        "source": hostname,
                        "target": addr,
                    }
                )

            # Extract TailscaleNetwork entities from subnet routes
            subnet_routes = device_raw.get("advertiseRoutes", [])
            for route in subnet_routes:
                if route not in seen_networks:
                    network_entity = self._extract_network_entity(route, now)
                    networks.append(network_entity)
                    seen_networks.add(route)

        logger.info(
            f"Extracted {len(devices)} devices, {len(networks)} networks, "
            f"{len(hosts)} hosts (legacy), {len(ips)} IPs (legacy), "
            f"{len(relationships)} relationships (legacy)"
        )

        return {
            # New format (Phase 4)
            "devices": devices,
            "networks": networks,
            "acls": acls,  # Empty for now, ACL extraction requires additional API calls
            # Legacy format (backward compatibility)
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
            data: dict[str, Any] = response.json()

            devices_raw: list[Any] = data.get("devices", [])
            # Validate that devices is a list of dicts
            if not isinstance(devices_raw, list):
                raise TailscaleAPIError(f"Expected 'devices' to be a list, got {type(devices_raw)}")

            devices: list[dict[str, Any]] = []
            for device in devices_raw:
                if not isinstance(device, dict):
                    logger.warning(f"Skipping non-dict device entry: {type(device)}")
                    continue
                devices.append(device)

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

    def _parse_timestamp(self, timestamp_str: str | None) -> datetime | None:
        """Parse ISO 8601 timestamp string to datetime object.

        Args:
            timestamp_str: ISO 8601 timestamp string (e.g., "2024-01-15T09:00:00Z").

        Returns:
            datetime | None: Parsed datetime object or None if invalid/missing.
        """
        if not timestamp_str:
            return None

        try:
            # Replace 'Z' suffix with '+00:00' for UTC timezone
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse timestamp: {timestamp_str}: {e}")
            return None

    def _extract_device_entity(self, device_raw: dict[str, Any], now: datetime) -> TailscaleDevice:
        """Extract TailscaleDevice entity from raw API response.

        Converts raw Tailscale API device data into a validated TailscaleDevice Pydantic
        model with temporal tracking metadata. Separates IPv4 and IPv6 addresses into
        distinct fields for queryability.

        Args:
            device_raw: Raw device data from Tailscale API containing device ID, hostname,
                       addresses, OS, and optional fields like exit node status and SSH config.
            now: Current timestamp for extraction metadata (created_at, updated_at).

        Returns:
            TailscaleDevice: Validated device entity with temporal tracking and extraction
                            metadata (tier, method, confidence, version).

        Note:
            - Takes first IPv4 and first IPv6 address if multiple present
            - key_expiry not available in basic /devices API endpoint
            - All extraction uses Tier A (deterministic API parsing)
        """
        # Parse addresses into IPv4 and IPv6
        addresses = device_raw.get("addresses", [])
        ipv4_address: str | None = None
        ipv6_address: str | None = None

        for addr in addresses:
            try:
                ip_obj = ipaddress.ip_address(addr)
                if isinstance(ip_obj, ipaddress.IPv4Address) and ipv4_address is None:
                    ipv4_address = addr
                elif isinstance(ip_obj, ipaddress.IPv6Address) and ipv6_address is None:
                    ipv6_address = addr
            except ValueError:
                logger.warning(f"Skipping invalid IP address: {addr}")
                continue

        # Parse last seen timestamp
        source_timestamp = self._parse_timestamp(device_raw.get("lastSeen"))

        # Create TailscaleDevice entity
        magic_dns_hostname = (
            device_raw.get("tailnetDNSName")
            or device_raw.get("dnsName")
            or device_raw.get("magicDNSName")
        )

        long_domain = device_raw.get("name")

        return TailscaleDevice(
            device_id=device_raw["id"],
            hostname=device_raw["hostname"],
            long_domain=long_domain,
            os=device_raw["os"],
            ipv4_address=ipv4_address,
            ipv6_address=ipv6_address,
            endpoints=device_raw.get("endpoints"),
            key_expiry=None,  # Not available in basic device API response
            is_exit_node=device_raw.get("isExitNode"),
            subnet_routes=device_raw.get("advertiseRoutes"),
            ssh_enabled=device_raw.get("enabledSSH"),
            tailnet_dns_name=magic_dns_hostname,
            created_at=now,
            updated_at=now,
            source_timestamp=source_timestamp,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version=EXTRACTOR_VERSION,
        )

    def _extract_network_entity(self, cidr: str, now: datetime) -> TailscaleNetwork:
        """Extract TailscaleNetwork entity from subnet route.

        Creates a TailscaleNetwork entity from a subnet route advertised by a device.
        Generates a deterministic network ID from the CIDR notation for consistent
        identification across extractions.

        Args:
            cidr: CIDR notation for subnet route (e.g., "10.0.0.0/24").
            now: Current timestamp for extraction metadata (created_at, updated_at).

        Returns:
            TailscaleNetwork: Validated network entity with temporal tracking and
                             extraction metadata. DNS and nameserver fields are None
                             as they're not available from subnet route data.

        Note:
            - Network ID is deterministic: "network-{cidr_sanitized}"
            - DNS configuration requires separate API calls (not implemented in Phase 4)
            - All extraction uses Tier A (deterministic API parsing)
        """
        # Generate network ID from CIDR (sanitize for use as identifier)
        network_id = f"network-{cidr.replace('/', '_').replace('.', '_').replace(':', '_')}"

        # Generate descriptive name from CIDR
        name = f"Subnet {cidr}"

        return TailscaleNetwork(
            network_id=network_id,
            name=name,
            cidr=cidr,
            global_nameservers=None,  # Not available from subnet routes
            search_domains=None,  # Not available from subnet routes
            created_at=now,
            updated_at=now,
            source_timestamp=None,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version=EXTRACTOR_VERSION,
        )
