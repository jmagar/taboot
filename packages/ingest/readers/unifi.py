"""Unifi Controller network topology reader for Taboot platform.

Parses Unifi Controller API and extracts:
- Host nodes (devices and clients with hostnames and MAC addresses)
- IP nodes (IPv4 and IPv6 addresses)
- LOCATED_AT relationships (Host → IP)

Per data-model.md: Extracts structured sources to nodes/edges deterministically.
"""

import ipaddress
import logging
import re
from typing import Any

import requests

logger = logging.getLogger(__name__)


class UnifiError(Exception):
    """Base exception for UnifiReader errors."""

    pass


class UnifiAuthError(UnifiError):
    """Raised when authentication with Unifi Controller fails."""

    pass


class UnifiConnectionError(UnifiError):
    """Raised when connection to Unifi Controller fails."""

    pass


class UnifiSSLError(UnifiError):
    """Raised when SSL certificate verification fails."""

    pass


class InvalidMACError(UnifiError):
    """Raised when MAC address format is invalid."""

    pass


class InvalidIPError(UnifiError):
    """Raised when IP address format is invalid."""

    pass


class UnifiReader:
    """Unifi Controller network topology reader.

    Connects to Unifi Controller API and extracts network topology:
    Host nodes, IP nodes, and LOCATED_AT relationships.
    """

    def __init__(
        self,
        controller_url: str,
        username: str,
        password: str,
        site: str = "default",
        verify_ssl: bool = True,
    ) -> None:
        """Initialize UnifiReader with controller credentials.

        Args:
            controller_url: URL of Unifi Controller (e.g., https://unifi.local:8443).
            username: Username for Unifi Controller.
            password: Password for Unifi Controller.
            site: Site name (default: "default").
            verify_ssl: Whether to verify SSL certificates (default: True).

        Raises:
            ValueError: If required parameters are empty.
        """
        if not controller_url:
            raise ValueError("controller_url cannot be empty")
        if not username:
            raise ValueError("username cannot be empty")
        if not password:
            raise ValueError("password cannot be empty")

        self.controller_url = controller_url.rstrip("/")
        self.username = username
        self.password = password
        self.site = site
        self.verify_ssl = verify_ssl
        self.session: requests.Session | None = None

        logger.info(
            f"Initialized UnifiReader (controller_url={controller_url}, "
            f"site={site}, verify_ssl={verify_ssl})"
        )

    def _login(self) -> None:
        """Authenticate with Unifi Controller.

        Raises:
            UnifiAuthError: If authentication fails.
            UnifiConnectionError: If connection fails.
            UnifiSSLError: If SSL verification fails.
        """
        if self.session is None:
            self.session = requests.Session()

        login_url = f"{self.controller_url}/api/login"
        payload = {
            "username": self.username,
            "password": self.password,
        }

        try:
            response = self.session.post(
                login_url,
                json=payload,
                verify=self.verify_ssl,
            )

            if response.status_code != 200:
                raise UnifiAuthError(f"Authentication failed with status {response.status_code}")

            data = response.json()
            if data.get("meta", {}).get("rc") != "ok":
                raise UnifiAuthError("Authentication failed: invalid credentials")

            logger.info("Successfully authenticated with Unifi Controller")

        except requests.exceptions.SSLError as e:
            raise UnifiSSLError(f"SSL certificate verification failed: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise UnifiConnectionError(f"Failed to connect to Unifi Controller: {e}") from e

    def _logout(self) -> None:
        """Logout from Unifi Controller."""
        if self.session is None:
            return

        try:
            logout_url = f"{self.controller_url}/api/logout"
            self.session.post(logout_url, verify=self.verify_ssl)
            logger.info("Logged out from Unifi Controller")
        except Exception as e:
            logger.warning(f"Failed to logout cleanly: {e}")
        finally:
            if self.session:
                self.session.close()
                self.session = None

    def _validate_mac_address(self, mac: str) -> None:
        """Validate MAC address format.

        Args:
            mac: MAC address string.

        Raises:
            InvalidMACError: If MAC address format is invalid.
        """
        # MAC address pattern: xx:xx:xx:xx:xx:xx (hex digits)
        mac_pattern = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
        if not mac_pattern.match(mac):
            raise InvalidMACError(f"Invalid MAC address format: {mac}")

    def _validate_ip_address(self, ip: str) -> str:
        """Validate IP address format and determine type.

        Args:
            ip: IP address string.

        Returns:
            str: IP type ("v4" or "v6").

        Raises:
            InvalidIPError: If IP address format is invalid.
        """
        try:
            addr = ipaddress.ip_address(ip)
            if isinstance(addr, ipaddress.IPv4Address):
                return "v4"
            elif isinstance(addr, ipaddress.IPv6Address):
                return "v6"
            else:
                raise InvalidIPError(f"Invalid IP address: {ip}")
        except ValueError as e:
            raise InvalidIPError(f"Invalid IP address: {ip}") from e

    def _fetch_devices(self) -> list[dict[str, Any]]:
        """Fetch device list from Unifi Controller.

        Returns:
            list[dict[str, Any]]: List of device data.

        Raises:
            UnifiError: If API request fails.
        """
        if self.session is None:
            raise UnifiError("Not authenticated - call _login() first")

        devices_url = f"{self.controller_url}/api/s/{self.site}/stat/device"

        try:
            response = self.session.post(devices_url, verify=self.verify_ssl)

            if response.status_code != 200:
                raise UnifiError(f"Failed to fetch devices: status {response.status_code}")

            data = response.json()
            if data.get("meta", {}).get("rc") != "ok":
                raise UnifiError("Failed to fetch devices: API error")

            devices_data: list[dict[str, Any]] = data.get("data", [])
            logger.info(f"Fetched {len(devices_data)} devices from Unifi Controller")
            return devices_data

        except requests.exceptions.RequestException as e:
            raise UnifiError(f"Failed to fetch devices: {e}") from e

    def _fetch_clients(self) -> list[dict[str, Any]]:
        """Fetch client list from Unifi Controller.

        Returns:
            list[dict[str, Any]]: List of client data.

        Raises:
            UnifiError: If API request fails.
        """
        if self.session is None:
            raise UnifiError("Not authenticated - call _login() first")

        clients_url = f"{self.controller_url}/api/s/{self.site}/stat/sta"

        try:
            response = self.session.post(clients_url, verify=self.verify_ssl)

            if response.status_code != 200:
                raise UnifiError(f"Failed to fetch clients: status {response.status_code}")

            data = response.json()
            if data.get("meta", {}).get("rc") != "ok":
                raise UnifiError("Failed to fetch clients: API error")

            clients_data: list[dict[str, Any]] = data.get("data", [])
            logger.info(f"Fetched {len(clients_data)} clients from Unifi Controller")
            return clients_data

        except requests.exceptions.RequestException as e:
            raise UnifiError(f"Failed to fetch clients: {e}") from e

    def load_data(self) -> dict[str, Any]:
        """Load and parse Unifi Controller network topology.

        Returns:
            dict[str, Any]: Structured data with hosts, IPs, and relationships.
                {
                    "hosts": [
                        {
                            "hostname": str,
                            "mac": str,
                            "metadata": dict,
                        },
                        ...
                    ],
                    "ips": [
                        {
                            "addr": str,
                            "ip_type": "v4" | "v6",
                            "allocation": "static" | "dhcp" | "unknown",
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
            UnifiAuthError: If authentication fails.
            UnifiConnectionError: If connection fails.
            UnifiSSLError: If SSL verification fails.
            InvalidMACError: If MAC address is invalid.
            InvalidIPError: If IP address is invalid.
        """
        logger.info("Loading Unifi network topology")

        try:
            # Authenticate
            self._login()

            # Fetch devices and clients
            devices = self._fetch_devices()
            clients = self._fetch_clients()

            # Extract data
            hosts: list[dict[str, Any]] = []
            ips: list[dict[str, Any]] = []
            relationships: list[dict[str, Any]] = []

            # Process devices
            for device in devices:
                mac = device.get("mac", "")
                ip = device.get("ip", "")
                name = device.get("name", "")

                if not mac or not ip or not name:
                    logger.warning(f"Skipping device with missing data: {device}")
                    continue

                # Validate MAC and IP
                self._validate_mac_address(mac)
                ip_type = self._validate_ip_address(ip)

                # Create host node
                hosts.append(
                    {
                        "hostname": name,
                        "mac": mac,
                        "metadata": {
                            "type": device.get("type", ""),
                            "model": device.get("model", ""),
                            "adopted": device.get("adopted", False),
                            "state": device.get("state", 0),
                        },
                    }
                )

                # Create IP node
                ips.append(
                    {
                        "addr": ip,
                        "ip_type": ip_type,
                        "allocation": "static",  # Devices typically have static IPs
                    }
                )

                # Create LOCATED_AT relationship
                relationships.append(
                    {
                        "type": "LOCATED_AT",
                        "source": name,
                        "target": ip,
                    }
                )

            # Process clients
            for client in clients:
                mac = client.get("mac", "")
                ip = client.get("ip", "")
                hostname = client.get("hostname", "")

                if not mac or not ip:
                    logger.warning(f"Skipping client with missing data: {client}")
                    continue

                # Use MAC as fallback hostname if not provided
                if not hostname:
                    hostname = mac
                    logger.debug(f"Using MAC as hostname for client: {mac}")

                # Validate MAC and IP
                self._validate_mac_address(mac)
                ip_type = self._validate_ip_address(ip)

                # Create host node
                hosts.append(
                    {
                        "hostname": hostname,
                        "mac": mac,
                        "metadata": {
                            "network": client.get("network", ""),
                            "is_wired": client.get("is_wired", False),
                        },
                    }
                )

                # Create IP node
                ips.append(
                    {
                        "addr": ip,
                        "ip_type": ip_type,
                        "allocation": "dhcp",  # Clients typically get DHCP IPs
                    }
                )

                # Create LOCATED_AT relationship
                relationships.append(
                    {
                        "type": "LOCATED_AT",
                        "source": hostname,
                        "target": ip,
                    }
                )

            logger.info(
                f"Extracted {len(hosts)} hosts, {len(ips)} IPs, "
                f"and {len(relationships)} relationships"
            )

            return {
                "hosts": hosts,
                "ips": ips,
                "relationships": relationships,
            }

        finally:
            # Always logout
            self._logout()
