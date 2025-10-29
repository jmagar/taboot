"""Unifi Controller network topology reader for Taboot platform.

Parses Unifi Controller API and extracts new entity types:
- UnifiDevice (network devices: switches, APs, gateways)
- UnifiClient (connected client devices)
- UnifiNetwork (VLANs and network configurations)
- UnifiSite (deployment sites)
- PortForwardingRule (DNAT port forwarding rules)
- FirewallRule (firewall policies)
- TrafficRule (traffic shaping/QoS rules)
- TrafficRoute (policy-based routing)
- NATRule (NAT rules)

Per data-model.md: Extracts structured sources to entities deterministically (Tier A).
"""

import ipaddress
import logging
import re
from datetime import UTC, datetime
from typing import Any

import requests

from packages.schemas.unifi import (
    FirewallRule,
    NATRule,
    PortForwardingRule,
    TrafficRoute,
    TrafficRule,
    UnifiClient,
    UnifiDevice,
    UnifiNetwork,
    UnifiSite,
)

logger = logging.getLogger(__name__)

# Version constant for extraction metadata
EXTRACTOR_VERSION = "1.0.0"


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

    def _fetch_sites(self) -> list[dict[str, Any]]:
        """Fetch site list from Unifi Controller.

        Returns:
            list[dict[str, Any]]: List of site data.

        Raises:
            UnifiError: If API request fails.
        """
        if self.session is None:
            raise UnifiError("Not authenticated - call _login() first")

        sites_url = f"{self.controller_url}/api/self/sites"

        try:
            response = self.session.post(sites_url, verify=self.verify_ssl)

            if response.status_code != 200:
                raise UnifiError(f"Failed to fetch sites: status {response.status_code}")

            data = response.json()
            if data.get("meta", {}).get("rc") != "ok":
                raise UnifiError("Failed to fetch sites: API error")

            sites_data: list[dict[str, Any]] = data.get("data", [])
            logger.info(f"Fetched {len(sites_data)} sites from Unifi Controller")
            return sites_data

        except requests.exceptions.RequestException as e:
            raise UnifiError(f"Failed to fetch sites: {e}") from e

    def _fetch_networks(self) -> list[dict[str, Any]]:
        """Fetch network list from Unifi Controller.

        Returns:
            list[dict[str, Any]]: List of network data.

        Raises:
            UnifiError: If API request fails.
        """
        if self.session is None:
            raise UnifiError("Not authenticated - call _login() first")

        networks_url = f"{self.controller_url}/api/s/{self.site}/rest/networkconf"

        try:
            response = self.session.post(networks_url, verify=self.verify_ssl)

            if response.status_code != 200:
                raise UnifiError(f"Failed to fetch networks: status {response.status_code}")

            data = response.json()
            if data.get("meta", {}).get("rc") != "ok":
                raise UnifiError("Failed to fetch networks: API error")

            networks_data: list[dict[str, Any]] = data.get("data", [])
            logger.info(f"Fetched {len(networks_data)} networks from Unifi Controller")
            return networks_data

        except requests.exceptions.RequestException as e:
            raise UnifiError(f"Failed to fetch networks: {e}") from e

    def _fetch_port_forwarding_rules(self) -> list[dict[str, Any]]:
        """Fetch port forwarding rules from Unifi Controller.

        Returns:
            list[dict[str, Any]]: List of port forwarding rule data.

        Raises:
            UnifiError: If API request fails.
        """
        if self.session is None:
            raise UnifiError("Not authenticated - call _login() first")

        portforward_url = f"{self.controller_url}/api/s/{self.site}/rest/portforward"

        try:
            response = self.session.post(portforward_url, verify=self.verify_ssl)

            if response.status_code != 200:
                raise UnifiError(
                    f"Failed to fetch port forwarding rules: status {response.status_code}"
                )

            data = response.json()
            if data.get("meta", {}).get("rc") != "ok":
                raise UnifiError("Failed to fetch port forwarding rules: API error")

            rules_data: list[dict[str, Any]] = data.get("data", [])
            logger.info(f"Fetched {len(rules_data)} port forwarding rules from Unifi Controller")
            return rules_data

        except requests.exceptions.RequestException as e:
            raise UnifiError(f"Failed to fetch port forwarding rules: {e}") from e

    def _fetch_firewall_rules(self) -> list[dict[str, Any]]:
        """Fetch firewall rules from Unifi Controller.

        Returns:
            list[dict[str, Any]]: List of firewall rule data.

        Raises:
            UnifiError: If API request fails.
        """
        if self.session is None:
            raise UnifiError("Not authenticated - call _login() first")

        firewall_url = f"{self.controller_url}/v2/api/site/{self.site}/firewall-policies"

        try:
            response = self.session.post(firewall_url, verify=self.verify_ssl)

            if response.status_code != 200:
                raise UnifiError(f"Failed to fetch firewall rules: status {response.status_code}")

            data = response.json()
            if data.get("meta", {}).get("rc") != "ok":
                raise UnifiError("Failed to fetch firewall rules: API error")

            rules_data: list[dict[str, Any]] = data.get("data", [])
            logger.info(f"Fetched {len(rules_data)} firewall rules from Unifi Controller")
            return rules_data

        except requests.exceptions.RequestException as e:
            raise UnifiError(f"Failed to fetch firewall rules: {e}") from e

    def _fetch_traffic_rules(self) -> list[dict[str, Any]]:
        """Fetch traffic rules from Unifi Controller.

        Returns:
            list[dict[str, Any]]: List of traffic rule data.

        Raises:
            UnifiError: If API request fails.
        """
        if self.session is None:
            raise UnifiError("Not authenticated - call _login() first")

        traffic_rules_url = f"{self.controller_url}/v2/api/site/{self.site}/trafficrules"

        try:
            response = self.session.post(traffic_rules_url, verify=self.verify_ssl)

            if response.status_code != 200:
                raise UnifiError(f"Failed to fetch traffic rules: status {response.status_code}")

            data = response.json()
            if data.get("meta", {}).get("rc") != "ok":
                raise UnifiError("Failed to fetch traffic rules: API error")

            rules_data: list[dict[str, Any]] = data.get("data", [])
            logger.info(f"Fetched {len(rules_data)} traffic rules from Unifi Controller")
            return rules_data

        except requests.exceptions.RequestException as e:
            raise UnifiError(f"Failed to fetch traffic rules: {e}") from e

    def _fetch_traffic_routes(self) -> list[dict[str, Any]]:
        """Fetch traffic routes from Unifi Controller.

        Returns:
            list[dict[str, Any]]: List of traffic route data.

        Raises:
            UnifiError: If API request fails.
        """
        if self.session is None:
            raise UnifiError("Not authenticated - call _login() first")

        traffic_routes_url = f"{self.controller_url}/v2/api/site/{self.site}/trafficroutes"

        try:
            response = self.session.post(traffic_routes_url, verify=self.verify_ssl)

            if response.status_code != 200:
                raise UnifiError(f"Failed to fetch traffic routes: status {response.status_code}")

            data = response.json()
            if data.get("meta", {}).get("rc") != "ok":
                raise UnifiError("Failed to fetch traffic routes: API error")

            routes_data: list[dict[str, Any]] = data.get("data", [])
            logger.info(f"Fetched {len(routes_data)} traffic routes from Unifi Controller")
            return routes_data

        except requests.exceptions.RequestException as e:
            raise UnifiError(f"Failed to fetch traffic routes: {e}") from e

    def _fetch_nat_rules(self) -> list[dict[str, Any]]:
        """Fetch NAT rules from Unifi Controller.

        Note: Unifi API has limited NAT rule support (DNAT only via PortForwardingRule).

        Returns:
            list[dict[str, Any]]: List of NAT rule data.

        Raises:
            UnifiError: If API request fails.
        """
        if self.session is None:
            raise UnifiError("Not authenticated - call _login() first")

        nat_rules_url = f"{self.controller_url}/api/s/{self.site}/rest/portforward"

        try:
            response = self.session.post(nat_rules_url, verify=self.verify_ssl)

            if response.status_code != 200:
                raise UnifiError(f"Failed to fetch NAT rules: status {response.status_code}")

            data = response.json()
            if data.get("meta", {}).get("rc") != "ok":
                raise UnifiError("Failed to fetch NAT rules: API error")

            rules_data: list[dict[str, Any]] = data.get("data", [])
            logger.info(f"Fetched {len(rules_data)} NAT rules from Unifi Controller")
            return rules_data

        except requests.exceptions.RequestException as e:
            raise UnifiError(f"Failed to fetch NAT rules: {e}") from e

    def load_data(self) -> dict[str, Any]:
        """Load and parse Unifi Controller network topology.

        Returns:
            dict[str, Any]: Structured data with new entity types.
                {
                    "devices": list[UnifiDevice],
                    "clients": list[UnifiClient],
                    "networks": list[UnifiNetwork],
                    "sites": list[UnifiSite],
                    "port_forwarding_rules": list[PortForwardingRule],
                    "firewall_rules": list[FirewallRule],
                    "traffic_rules": list[TrafficRule],
                    "traffic_routes": list[TrafficRoute],
                    "nat_rules": list[NATRule],
                }

        Raises:
            UnifiAuthError: If authentication fails.
            UnifiConnectionError: If connection fails.
            UnifiSSLError: If SSL verification fails.
        """
        logger.info("Loading Unifi network topology with new entity types")

        try:
            # Authenticate
            self._login()

            # Fetch all data
            sites_data = self._fetch_sites()
            devices_data = self._fetch_devices()
            clients_data = self._fetch_clients()
            networks_data = self._fetch_networks()
            portforward_data = self._fetch_port_forwarding_rules()
            firewall_data = self._fetch_firewall_rules()
            traffic_rules_data = self._fetch_traffic_rules()
            traffic_routes_data = self._fetch_traffic_routes()
            nat_rules_data = self._fetch_nat_rules()

            # Extract entities with temporal tracking
            now = datetime.now(UTC)

            # Extract sites
            sites: list[UnifiSite] = []
            for site_raw in sites_data:
                try:
                    site = UnifiSite(
                        site_id=site_raw.get("_id", site_raw.get("name", "unknown")),
                        name=site_raw.get("name", ""),
                        description=site_raw.get("desc"),
                        wan_ip=(
                            site_raw.get("wan", {}).get("ip")
                            if isinstance(site_raw.get("wan"), dict)
                            else None
                        ),
                        gateway_ip=None,  # Not available in site API
                        dns_servers=None,  # Not available in site API
                        created_at=now,
                        updated_at=now,
                        source_timestamp=None,
                        extraction_tier="A",
                        extraction_method="unifi_api",
                        confidence=1.0,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                    sites.append(site)
                except Exception as e:
                    logger.warning(f"Failed to parse site {site_raw.get('_id')}: {e}")

            # Extract devices
            devices: list[UnifiDevice] = []
            for device_raw in devices_data:
                try:
                    uplink = device_raw.get("uplink", {})
                    device = UnifiDevice(
                        mac=device_raw["mac"],
                        hostname=device_raw["name"],
                        type=device_raw.get("type", "unknown"),
                        model=device_raw.get("model", "unknown"),
                        adopted=device_raw.get("adopted", False),
                        state=device_raw.get("state", "unknown"),
                        ip=device_raw.get("ip"),
                        firmware_version=device_raw.get("version"),
                        link_speed=uplink.get("speed") if isinstance(uplink, dict) else None,
                        connection_type=uplink.get("type") if isinstance(uplink, dict) else None,
                        uptime=device_raw.get("uptime"),
                        created_at=now,
                        updated_at=now,
                        source_timestamp=None,
                        extraction_tier="A",
                        extraction_method="unifi_api",
                        confidence=1.0,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                    devices.append(device)
                except Exception as e:
                    logger.warning(f"Failed to parse device {device_raw.get('mac')}: {e}")

            # Extract clients
            clients: list[UnifiClient] = []
            for client_raw in clients_data:
                try:
                    uplink = client_raw.get("uplink", {})
                    client = UnifiClient(
                        mac=client_raw["mac"],
                        hostname=client_raw.get("hostname", client_raw["mac"]),
                        ip=client_raw["ip"],
                        network=client_raw.get("network", ""),
                        is_wired=client_raw.get("is_wired", False),
                        link_speed=uplink.get("speed") if isinstance(uplink, dict) else None,
                        connection_type=uplink.get("type") if isinstance(uplink, dict) else None,
                        uptime=client_raw.get("uptime"),
                        created_at=now,
                        updated_at=now,
                        source_timestamp=None,
                        extraction_tier="A",
                        extraction_method="unifi_api",
                        confidence=1.0,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                    clients.append(client)
                except Exception as e:
                    logger.warning(f"Failed to parse client {client_raw.get('mac')}: {e}")

            # Extract networks
            networks: list[UnifiNetwork] = []
            for network_raw in networks_data:
                try:
                    network = UnifiNetwork(
                        network_id=network_raw["_id"],
                        name=network_raw["name"],
                        vlan_id=network_raw.get("vlan", 1),
                        subnet=network_raw.get("ip_subnet", ""),
                        gateway_ip=network_raw.get("gateway_ip", ""),
                        dns_servers=network_raw.get("nameservers"),
                        wifi_name=network_raw.get("essid"),
                        created_at=now,
                        updated_at=now,
                        source_timestamp=None,
                        extraction_tier="A",
                        extraction_method="unifi_api",
                        confidence=1.0,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                    networks.append(network)
                except Exception as e:
                    logger.warning(f"Failed to parse network {network_raw.get('_id')}: {e}")

            # Extract port forwarding rules
            port_forwarding_rules: list[PortForwardingRule] = []
            for rule_raw in portforward_data:
                try:
                    pf_rule = PortForwardingRule(
                        rule_id=rule_raw["_id"],
                        name=rule_raw["name"],
                        enabled=rule_raw.get("enabled", False),
                        proto=rule_raw.get("proto", "tcp"),
                        src=rule_raw.get("src", "any"),
                        dst_port=int(rule_raw.get("dst_port", 0)),
                        fwd=rule_raw["fwd"],
                        fwd_port=int(rule_raw.get("fwd_port", 0)),
                        pfwd_interface=rule_raw.get("pfwd_interface"),
                        created_at=now,
                        updated_at=now,
                        source_timestamp=None,
                        extraction_tier="A",
                        extraction_method="unifi_api",
                        confidence=1.0,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                    port_forwarding_rules.append(pf_rule)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse port forwarding rule {rule_raw.get('_id')}: {e}"
                    )

            # Extract firewall rules
            firewall_rules: list[FirewallRule] = []
            for rule_raw in firewall_data:
                try:
                    fw_rule = FirewallRule(
                        rule_id=rule_raw["_id"],
                        name=rule_raw["name"],
                        enabled=rule_raw.get("enabled", False),
                        action=rule_raw.get("action", "DROP"),
                        protocol=rule_raw.get("protocol", "all"),
                        ip_version=rule_raw.get("ip_version", "ipv4"),
                        index=rule_raw.get("rule_index", 0),
                        source_zone=rule_raw.get("src_firewall_group"),
                        dest_zone=rule_raw.get("dst_firewall_group"),
                        logging=rule_raw.get("logging"),
                        created_at=now,
                        updated_at=now,
                        source_timestamp=None,
                        extraction_tier="A",
                        extraction_method="unifi_api",
                        confidence=1.0,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                    firewall_rules.append(fw_rule)
                except Exception as e:
                    logger.warning(f"Failed to parse firewall rule {rule_raw.get('_id')}: {e}")

            # Extract traffic rules
            traffic_rules: list[TrafficRule] = []
            for rule_raw in traffic_rules_data:
                try:
                    # Handle bandwidth_limit - if it's an int, convert to proper dict format
                    bandwidth_limit = rule_raw.get("bandwidth_limit")
                    if isinstance(bandwidth_limit, int):
                        # Convert legacy int format to dict
                        bandwidth_limit = {
                            "download_kbps": bandwidth_limit,
                            "upload_kbps": bandwidth_limit,
                        }
                    elif not isinstance(bandwidth_limit, dict):
                        bandwidth_limit = None

                    # Handle schedule - if it's a bool or dict, convert to string
                    schedule = rule_raw.get("schedule")
                    if isinstance(schedule, dict):
                        schedule = "enabled" if schedule.get("enabled") else "disabled"
                    elif isinstance(schedule, bool):
                        schedule = "enabled" if schedule else "disabled"
                    elif not isinstance(schedule, str):
                        schedule = None

                    tr_rule = TrafficRule(
                        rule_id=rule_raw["_id"],
                        name=rule_raw["name"],
                        enabled=rule_raw.get("enabled", False),
                        action=rule_raw.get("action", "limit"),
                        bandwidth_limit=bandwidth_limit,
                        matching_target=rule_raw.get("matching_target"),
                        ip_addresses=rule_raw.get("target_ip"),
                        domains=rule_raw.get("domains"),
                        schedule=schedule,
                        created_at=now,
                        updated_at=now,
                        source_timestamp=None,
                        extraction_tier="A",
                        extraction_method="unifi_api",
                        confidence=1.0,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                    traffic_rules.append(tr_rule)
                except Exception as e:
                    logger.warning(f"Failed to parse traffic rule {rule_raw.get('_id')}: {e}")

            # Extract traffic routes
            traffic_routes: list[TrafficRoute] = []
            for route_raw in traffic_routes_data:
                try:
                    t_route = TrafficRoute(
                        route_id=route_raw["_id"],
                        name=route_raw.get("description", ""),
                        enabled=route_raw.get("enabled", False),
                        next_hop=route_raw["next_hop"],
                        matching_target=route_raw.get("matching_target"),
                        network_id=route_raw.get("network_id"),
                        ip_addresses=route_raw.get("target_ip"),
                        domains=route_raw.get("domains"),
                        created_at=now,
                        updated_at=now,
                        source_timestamp=None,
                        extraction_tier="A",
                        extraction_method="unifi_api",
                        confidence=1.0,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                    traffic_routes.append(t_route)
                except Exception as e:
                    logger.warning(f"Failed to parse traffic route {route_raw.get('_id')}: {e}")

            # Extract NAT rules (same as port forwarding for now)
            nat_rules: list[NATRule] = []
            for rule_raw in nat_rules_data:
                try:
                    nat_rule = NATRule(
                        rule_id=rule_raw["_id"],
                        name=rule_raw["name"],
                        enabled=rule_raw.get("enabled", False),
                        type=rule_raw.get("type", "dnat"),
                        source=rule_raw.get("src", "any"),
                        destination=rule_raw.get("dst", rule_raw.get("fwd", "")),
                        created_at=now,
                        updated_at=now,
                        source_timestamp=None,
                        extraction_tier="A",
                        extraction_method="unifi_api",
                        confidence=1.0,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                    nat_rules.append(nat_rule)
                except Exception as e:
                    logger.warning(f"Failed to parse NAT rule {rule_raw.get('_id')}: {e}")

            logger.info(
                f"Extracted {len(devices)} devices, {len(clients)} clients, "
                f"{len(networks)} networks, {len(sites)} sites, "
                f"{len(port_forwarding_rules)} port forwarding rules, "
                f"{len(firewall_rules)} firewall rules, {len(traffic_rules)} traffic rules, "
                f"{len(traffic_routes)} traffic routes, {len(nat_rules)} NAT rules"
            )

            return {
                "devices": devices,
                "clients": clients,
                "networks": networks,
                "sites": sites,
                "port_forwarding_rules": port_forwarding_rules,
                "firewall_rules": firewall_rules,
                "traffic_rules": traffic_rules,
                "traffic_routes": traffic_routes,
                "nat_rules": nat_rules,
            }

        finally:
            # Always logout
            self._logout()
