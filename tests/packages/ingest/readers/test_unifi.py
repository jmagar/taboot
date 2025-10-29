"""Tests for UnifiReader.

Tests Unifi Controller API client following TDD methodology (RED-GREEN-REFACTOR).
Extracts network topology using new entity types: UnifiDevice, UnifiClient, UnifiNetwork, UnifiSite,
PortForwardingRule, FirewallRule, TrafficRule, TrafficRoute, NATRule.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

import pytest

if TYPE_CHECKING:
    from packages.ingest.readers.unifi import UnifiReader
else:
    UnifiReader = Any


class TestUnifiReader:
    """Tests for the UnifiReader class."""

    @pytest.fixture
    def mock_devices_response(self) -> list[dict]:
        """Create mock Unifi device list response.

        Returns:
            list[dict]: Mock device data from Unifi Controller API.
        """
        return [
            {
                "name": "USG-Pro-4",
                "type": "usw",
                "mac": "aa:bb:cc:dd:ee:01",
                "ip": "192.168.1.1",
                "state": 1,
                "adopted": True,
                "model": "US8P150",
            },
            {
                "name": "Switch-24-PoE",
                "type": "usw",
                "mac": "aa:bb:cc:dd:ee:02",
                "ip": "192.168.1.2",
                "state": 1,
                "adopted": True,
                "model": "US24P250",
            },
            {
                "name": "AP-AC-Pro",
                "type": "uap",
                "mac": "aa:bb:cc:dd:ee:03",
                "ip": "192.168.1.10",
                "state": 1,
                "adopted": True,
                "model": "U7PG2",
            },
        ]

    @pytest.fixture
    def mock_clients_response(self) -> list[dict]:
        """Create mock Unifi client list response.

        Returns:
            list[dict]: Mock client data from Unifi Controller API.
        """
        return [
            {
                "hostname": "laptop-01",
                "mac": "11:22:33:44:55:01",
                "ip": "192.168.1.100",
                "network": "LAN",
                "is_wired": True,
            },
            {
                "hostname": "phone-02",
                "mac": "11:22:33:44:55:02",
                "ip": "192.168.1.101",
                "network": "LAN",
                "is_wired": False,
            },
            {
                "hostname": "",  # Client without hostname
                "mac": "11:22:33:44:55:03",
                "ip": "192.168.1.102",
                "network": "Guest",
                "is_wired": False,
            },
        ]

    @pytest.fixture
    def unifi_reader(self) -> UnifiReader:
        """Create UnifiReader instance for testing.

        Returns:
            UnifiReader: Configured reader instance.
        """
        from packages.ingest.readers.unifi import UnifiReader

        return UnifiReader(
            controller_url="https://unifi.local:8443",
            username="admin",
            password="secret",
            site="default",
            verify_ssl=False,
        )

    def test_reader_initializes_with_credentials(self) -> None:
        """Test that UnifiReader initializes with required credentials."""
        from packages.ingest.readers.unifi import UnifiReader

        reader = UnifiReader(
            controller_url="https://unifi.local:8443",
            username="admin",
            password="secret",
            site="default",
        )

        assert reader.controller_url == "https://unifi.local:8443"
        assert reader.username == "admin"
        assert reader.password == "secret"
        assert reader.site == "default"
        assert reader.verify_ssl is True  # Default

    def test_reader_requires_controller_url(self) -> None:
        """Test that UnifiReader requires controller_url parameter."""
        from packages.ingest.readers.unifi import UnifiReader

        with pytest.raises(ValueError, match="controller_url cannot be empty"):
            UnifiReader(
                controller_url="",
                username="admin",
                password="secret",
            )

    def test_reader_requires_username(self) -> None:
        """Test that UnifiReader requires username parameter."""
        from packages.ingest.readers.unifi import UnifiReader

        with pytest.raises(ValueError, match="username cannot be empty"):
            UnifiReader(
                controller_url="https://unifi.local:8443",
                username="",
                password="secret",
            )

    def test_reader_requires_password(self) -> None:
        """Test that UnifiReader requires password parameter."""
        from packages.ingest.readers.unifi import UnifiReader

        with pytest.raises(ValueError, match="password cannot be empty"):
            UnifiReader(
                controller_url="https://unifi.local:8443",
                username="admin",
                password="",
            )

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_authenticates_with_controller(
        self, mock_session_class: Mock, unifi_reader: UnifiReader
    ) -> None:
        """Test that UnifiReader authenticates with Unifi Controller."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock successful login response
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"meta": {"rc": "ok"}}
        mock_session.post.return_value = mock_login_response

        unifi_reader._login()

        # Verify login request was made
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "api/login" in call_args[0][0]
        assert call_args[1]["json"]["username"] == "admin"
        assert call_args[1]["json"]["password"] == "secret"

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_handles_authentication_failure(
        self, mock_session_class: Mock, unifi_reader: UnifiReader
    ) -> None:
        """Test that UnifiReader raises error on authentication failure."""
        from packages.ingest.readers.unifi import UnifiAuthError

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock failed login response
        mock_login_response = Mock()
        mock_login_response.status_code = 401
        mock_login_response.json.return_value = {"meta": {"rc": "error"}}
        mock_session.post.return_value = mock_login_response

        with pytest.raises(UnifiAuthError, match="Authentication failed"):
            unifi_reader._login()

    # Old tests removed - these tested the OLD entity format (hosts, ips, relationships)
    # The comprehensive integration test test_reader_extracts_new_entity_types
    # covers all the new entity types (UnifiDevice, UnifiClient, etc.)

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_handles_network_errors(
        self, mock_session_class: Mock, unifi_reader: UnifiReader
    ) -> None:
        """Test that UnifiReader handles network connection errors."""
        from packages.ingest.readers.unifi import UnifiConnectionError

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Simulate network error
        import requests

        mock_session.post.side_effect = requests.exceptions.ConnectionError("Network error")

        with pytest.raises(UnifiConnectionError, match="Failed to connect"):
            unifi_reader.load_data()

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_handles_ssl_errors(
        self, mock_session_class: Mock, unifi_reader: UnifiReader
    ) -> None:
        """Test that UnifiReader handles SSL certificate errors."""
        from packages.ingest.readers.unifi import UnifiSSLError

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Simulate SSL error
        import requests

        mock_session.post.side_effect = requests.exceptions.SSLError("SSL error")

        with pytest.raises(UnifiSSLError, match="SSL certificate verification failed"):
            unifi_reader.load_data()

    # Old tests removed - tested OLD entity format
    # See test_reader_extracts_new_entity_types for comprehensive coverage

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_extracts_new_entity_types(
        self, mock_session_class: Mock, unifi_reader: UnifiReader
    ) -> None:
        """Integration test: UnifiReader extracts all new entity types.

        This test verifies that UnifiReader correctly extracts:
        - UnifiDevice entities (from devices API)
        - UnifiClient entities (from clients API)
        - UnifiNetwork entities (from networks API)
        - UnifiSite entities (from sites API)
        - PortForwardingRule entities (from port forwarding API)
        - FirewallRule entities (from firewall API)
        - TrafficRule entities (from traffic rules API)
        - TrafficRoute entities (from traffic routes API)
        - NATRule entities (from NAT rules API)
        """
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

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock login response
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"meta": {"rc": "ok"}}

        # Mock site response
        mock_site_response = Mock()
        mock_site_response.status_code = 200
        mock_site_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "_id": "default",
                    "name": "Default Site",
                    "desc": "Main office",
                }
            ],
        }

        # Mock devices response
        mock_devices_response = Mock()
        mock_devices_response.status_code = 200
        mock_devices_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "mac": "aa:bb:cc:dd:ee:01",
                    "name": "USG-Pro-4",
                    "type": "ugw",
                    "model": "USG-PRO-4",
                    "adopted": True,
                    "state": "connected",
                    "ip": "192.168.1.1",
                    "version": "6.5.55",
                    "uplink": {"speed": 1000, "type": "wired"},
                    "uptime": 86400,
                }
            ],
        }

        # Mock clients response
        mock_clients_response = Mock()
        mock_clients_response.status_code = 200
        mock_clients_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "mac": "11:22:33:44:55:01",
                    "hostname": "laptop-01",
                    "ip": "192.168.1.100",
                    "network": "LAN",
                    "is_wired": True,
                    "uplink": {"speed": 1000, "type": "ethernet"},
                    "uptime": 7200,
                }
            ],
        }

        # Mock networks response
        mock_networks_response = Mock()
        mock_networks_response.status_code = 200
        mock_networks_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "_id": "5f9c1234abcd5678ef123456",
                    "name": "LAN",
                    "vlan": 1,
                    "ip_subnet": "192.168.1.0/24",
                    "gateway_ip": "192.168.1.1",
                    "nameservers": ["8.8.8.8", "8.8.4.4"],
                    "essid": "MyWiFi",
                }
            ],
        }

        # Mock port forwarding rules response
        mock_portforward_response = Mock()
        mock_portforward_response.status_code = 200
        mock_portforward_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "_id": "portfwd-001",
                    "name": "SSH Forward",
                    "enabled": True,
                    "proto": "tcp",
                    "src": "any",
                    "dst_port": "22",
                    "fwd": "192.168.1.100",
                    "fwd_port": "22",
                    "pfwd_interface": "wan",
                }
            ],
        }

        # Mock firewall rules response
        mock_firewall_response = Mock()
        mock_firewall_response.status_code = 200
        mock_firewall_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "_id": "firewall-001",
                    "name": "Allow HTTPS",
                    "enabled": True,
                    "action": "accept",
                    "protocol": "tcp",
                    "ip_version": "v4",
                    "rule_index": 1,
                    "src_firewall_group": "WAN",
                    "dst_firewall_group": "LAN",
                    "logging": True,
                }
            ],
        }

        # Mock traffic rules response
        mock_traffic_rules_response = Mock()
        mock_traffic_rules_response.status_code = 200
        mock_traffic_rules_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "_id": "traffic-rule-001",
                    "name": "IoT Rate Limit",
                    "enabled": True,
                    "action": "limit",
                    "bandwidth_limit": 10000,
                    "matching_target": "INTERNET",
                    "target_ip": ["192.168.2.0/24"],
                    "domains": [],
                    "schedule": {"enabled": False},
                }
            ],
        }

        # Mock traffic routes response
        mock_traffic_routes_response = Mock()
        mock_traffic_routes_response.status_code = 200
        mock_traffic_routes_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "_id": "traffic-route-001",
                    "description": "VPN Route",
                    "enabled": True,
                    "next_hop": "10.0.0.1",
                    "matching_target": "DOMAIN",
                    "network_id": "5f9c1234abcd5678ef123456",
                    "target_ip": [],
                    "domains": ["example.com"],
                }
            ],
        }

        # Mock NAT rules response
        mock_nat_rules_response = Mock()
        mock_nat_rules_response.status_code = 200
        mock_nat_rules_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "_id": "nat-rule-001",
                    "name": "Masquerade",
                    "enabled": True,
                    "type": "MASQUERADE",
                    "src": "192.168.1.0/24",
                    "dst": "0.0.0.0/0",
                }
            ],
        }

        mock_session.post.side_effect = [
            mock_login_response,
            mock_site_response,
            mock_devices_response,
            mock_clients_response,
            mock_networks_response,
            mock_portforward_response,
            mock_firewall_response,
            mock_traffic_rules_response,
            mock_traffic_routes_response,
            mock_nat_rules_response,
        ]

        result = unifi_reader.load_data()

        # Verify top-level structure
        assert isinstance(result, dict)
        assert "devices" in result
        assert "clients" in result
        assert "networks" in result
        assert "sites" in result
        assert "port_forwarding_rules" in result
        assert "firewall_rules" in result
        assert "traffic_rules" in result
        assert "traffic_routes" in result
        assert "nat_rules" in result

        # Verify UnifiDevice extraction
        devices = result["devices"]
        assert len(devices) == 1
        device = devices[0]
        assert isinstance(device, UnifiDevice)
        assert device.mac == "aa:bb:cc:dd:ee:01"
        assert device.hostname == "USG-Pro-4"
        assert device.type == "ugw"
        assert device.model == "USG-PRO-4"
        assert device.adopted is True
        assert device.state == "connected"
        assert device.ip == "192.168.1.1"
        assert device.firmware_version == "6.5.55"
        assert device.link_speed == 1000
        assert device.connection_type == "wired"
        assert device.uptime == 86400
        assert device.extraction_tier == "A"
        assert device.extraction_method == "unifi_api"
        assert device.confidence == 1.0

        # Verify UnifiClient extraction
        clients = result["clients"]
        assert len(clients) == 1
        client = clients[0]
        assert isinstance(client, UnifiClient)
        assert client.mac == "11:22:33:44:55:01"
        assert client.hostname == "laptop-01"
        assert client.ip == "192.168.1.100"
        assert client.network == "LAN"
        assert client.is_wired is True
        assert client.link_speed == 1000
        assert client.connection_type == "ethernet"
        assert client.uptime == 7200
        assert client.extraction_tier == "A"
        assert client.extraction_method == "unifi_api"
        assert client.confidence == 1.0

        # Verify UnifiNetwork extraction
        networks = result["networks"]
        assert len(networks) == 1
        network = networks[0]
        assert isinstance(network, UnifiNetwork)
        assert network.network_id == "5f9c1234abcd5678ef123456"
        assert network.name == "LAN"
        assert network.vlan_id == 1
        assert network.subnet == "192.168.1.0/24"
        assert network.gateway_ip == "192.168.1.1"
        assert network.dns_servers == ["8.8.8.8", "8.8.4.4"]
        assert network.wifi_name == "MyWiFi"
        assert network.extraction_tier == "A"

        # Verify UnifiSite extraction
        sites = result["sites"]
        assert len(sites) == 1
        site = sites[0]
        assert isinstance(site, UnifiSite)
        assert site.site_id == "default"
        assert site.name == "Default Site"
        assert site.description == "Main office"
        assert site.extraction_tier == "A"

        # Verify PortForwardingRule extraction
        port_forwarding_rules = result["port_forwarding_rules"]
        assert len(port_forwarding_rules) == 1
        pf_rule = port_forwarding_rules[0]
        assert isinstance(pf_rule, PortForwardingRule)
        assert pf_rule.rule_id == "portfwd-001"
        assert pf_rule.name == "SSH Forward"
        assert pf_rule.enabled is True
        assert pf_rule.proto == "tcp"
        assert pf_rule.src == "any"
        assert pf_rule.dst_port == 22
        assert pf_rule.fwd == "192.168.1.100"
        assert pf_rule.fwd_port == 22
        assert pf_rule.pfwd_interface == "wan"
        assert pf_rule.extraction_tier == "A"

        # Verify FirewallRule extraction
        firewall_rules = result["firewall_rules"]
        assert len(firewall_rules) == 1
        fw_rule = firewall_rules[0]
        assert isinstance(fw_rule, FirewallRule)
        assert fw_rule.rule_id == "firewall-001"
        assert fw_rule.name == "Allow HTTPS"
        assert fw_rule.enabled is True
        assert fw_rule.action == "accept"
        assert fw_rule.protocol == "tcp"
        assert fw_rule.ip_version == "v4"
        assert fw_rule.index == 1
        assert fw_rule.source_zone == "WAN"
        assert fw_rule.dest_zone == "LAN"
        assert fw_rule.logging is True
        assert fw_rule.extraction_tier == "A"

        # Verify TrafficRule extraction
        traffic_rules = result["traffic_rules"]
        assert len(traffic_rules) == 1
        tr_rule = traffic_rules[0]
        assert isinstance(tr_rule, TrafficRule)
        assert tr_rule.rule_id == "traffic-rule-001"
        assert tr_rule.name == "IoT Rate Limit"
        assert tr_rule.enabled is True
        assert tr_rule.action == "limit"
        # Reader converts int bandwidth_limit to dict format
        assert tr_rule.bandwidth_limit == {"download_kbps": 10000, "upload_kbps": 10000}
        assert tr_rule.matching_target == "INTERNET"
        assert tr_rule.ip_addresses == ["192.168.2.0/24"]
        assert tr_rule.domains == []
        assert tr_rule.extraction_tier == "A"

        # Verify TrafficRoute extraction
        traffic_routes = result["traffic_routes"]
        assert len(traffic_routes) == 1
        t_route = traffic_routes[0]
        assert isinstance(t_route, TrafficRoute)
        assert t_route.route_id == "traffic-route-001"
        assert t_route.name == "VPN Route"
        assert t_route.enabled is True
        assert t_route.next_hop == "10.0.0.1"
        assert t_route.matching_target == "DOMAIN"
        assert t_route.network_id == "5f9c1234abcd5678ef123456"
        assert t_route.ip_addresses == []
        assert t_route.domains == ["example.com"]
        assert t_route.extraction_tier == "A"

        # Verify NATRule extraction
        nat_rules = result["nat_rules"]
        assert len(nat_rules) == 1
        nat_rule = nat_rules[0]
        assert isinstance(nat_rule, NATRule)
        assert nat_rule.rule_id == "nat-rule-001"
        assert nat_rule.name == "Masquerade"
        assert nat_rule.enabled is True
        assert nat_rule.type == "MASQUERADE"
        assert nat_rule.source == "192.168.1.0/24"
        assert nat_rule.destination == "0.0.0.0/0"
        assert nat_rule.extraction_tier == "A"
