"""Tests for UnifiReader.

Tests Unifi Controller API client following TDD methodology (RED-GREEN-REFACTOR).
Extracts network topology: devices, clients, Host nodes, IP nodes, LOCATED_AT relationships.
"""

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

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_extracts_devices(
        self,
        mock_session_class: Mock,
        unifi_reader: UnifiReader,
        mock_devices_response: list[dict],
    ) -> None:
        """Test that UnifiReader extracts device topology."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock login
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"meta": {"rc": "ok"}}

        # Mock devices API response
        mock_devices_api_response = Mock()
        mock_devices_api_response.status_code = 200
        mock_devices_api_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": mock_devices_response,
        }

        # Mock clients API response (empty for this test)
        mock_clients_api_response = Mock()
        mock_clients_api_response.status_code = 200
        mock_clients_api_response.json.return_value = {"meta": {"rc": "ok"}, "data": []}

        mock_session.post.side_effect = [
            mock_login_response,
            mock_devices_api_response,
            mock_clients_api_response,
        ]

        result = unifi_reader.load_data()

        # Verify device extraction
        assert "hosts" in result
        hosts = result["hosts"]
        assert len(hosts) == 3

        # Verify device names extracted
        hostnames = {host["hostname"] for host in hosts}
        assert hostnames == {"USG-Pro-4", "Switch-24-PoE", "AP-AC-Pro"}

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_extracts_clients(
        self,
        mock_session_class: Mock,
        unifi_reader: UnifiReader,
        mock_clients_response: list[dict],
    ) -> None:
        """Test that UnifiReader extracts client information."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock login
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"meta": {"rc": "ok"}}

        # Mock devices API response (empty for this test)
        mock_devices_api_response = Mock()
        mock_devices_api_response.status_code = 200
        mock_devices_api_response.json.return_value = {"meta": {"rc": "ok"}, "data": []}

        # Mock clients API response
        mock_clients_api_response = Mock()
        mock_clients_api_response.status_code = 200
        mock_clients_api_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": mock_clients_response,
        }

        mock_session.post.side_effect = [
            mock_login_response,
            mock_devices_api_response,
            mock_clients_api_response,
        ]

        result = unifi_reader.load_data()

        # Verify client extraction
        assert "hosts" in result
        hosts = result["hosts"]
        assert len(hosts) == 3  # 2 with hostnames + 1 MAC-based fallback

        # Verify hostnames extracted
        hostnames = {host["hostname"] for host in hosts if not host["hostname"].startswith("11:22")}
        assert hostnames == {"laptop-01", "phone-02"}

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_extracts_ip_addresses(
        self,
        mock_session_class: Mock,
        unifi_reader: UnifiReader,
        mock_devices_response: list[dict],
    ) -> None:
        """Test that UnifiReader extracts IP address nodes."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock responses
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"meta": {"rc": "ok"}}

        mock_devices_api_response = Mock()
        mock_devices_api_response.status_code = 200
        mock_devices_api_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": mock_devices_response,
        }

        mock_clients_api_response = Mock()
        mock_clients_api_response.status_code = 200
        mock_clients_api_response.json.return_value = {"meta": {"rc": "ok"}, "data": []}

        mock_session.post.side_effect = [
            mock_login_response,
            mock_devices_api_response,
            mock_clients_api_response,
        ]

        result = unifi_reader.load_data()

        # Verify IP extraction
        assert "ips" in result
        ips = result["ips"]
        assert len(ips) == 3

        # Verify IP addresses extracted
        ip_addrs = {ip["addr"] for ip in ips}
        assert ip_addrs == {"192.168.1.1", "192.168.1.2", "192.168.1.10"}

        # Verify IP type (all should be v4)
        assert all(ip["ip_type"] == "v4" for ip in ips)

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_creates_located_at_relationships(
        self,
        mock_session_class: Mock,
        unifi_reader: UnifiReader,
        mock_devices_response: list[dict],
    ) -> None:
        """Test that UnifiReader creates LOCATED_AT relationships."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock responses
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"meta": {"rc": "ok"}}

        mock_devices_api_response = Mock()
        mock_devices_api_response.status_code = 200
        mock_devices_api_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": mock_devices_response,
        }

        mock_clients_api_response = Mock()
        mock_clients_api_response.status_code = 200
        mock_clients_api_response.json.return_value = {"meta": {"rc": "ok"}, "data": []}

        mock_session.post.side_effect = [
            mock_login_response,
            mock_devices_api_response,
            mock_clients_api_response,
        ]

        result = unifi_reader.load_data()

        # Verify LOCATED_AT relationships
        assert "relationships" in result
        relationships = result["relationships"]

        located_at = [r for r in relationships if r["type"] == "LOCATED_AT"]
        assert len(located_at) == 3

        # Verify relationship structure
        for rel in located_at:
            assert "source" in rel
            assert "target" in rel
            assert rel["source"] in {"USG-Pro-4", "Switch-24-PoE", "AP-AC-Pro"}
            assert rel["target"] in {"192.168.1.1", "192.168.1.2", "192.168.1.10"}

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_validates_mac_addresses(
        self, mock_session_class: Mock, unifi_reader: UnifiReader
    ) -> None:
        """Test that UnifiReader validates MAC address format."""
        from packages.ingest.readers.unifi import InvalidMACError

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock responses with invalid MAC
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"meta": {"rc": "ok"}}

        mock_devices_api_response = Mock()
        mock_devices_api_response.status_code = 200
        mock_devices_api_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "name": "Device",
                    "mac": "INVALID_MAC",
                    "ip": "192.168.1.1",
                    "state": 1,
                }
            ],
        }

        mock_clients_api_response = Mock()
        mock_clients_api_response.status_code = 200
        mock_clients_api_response.json.return_value = {"meta": {"rc": "ok"}, "data": []}

        mock_session.post.side_effect = [
            mock_login_response,
            mock_devices_api_response,
            mock_clients_api_response,
        ]

        with pytest.raises(InvalidMACError, match="Invalid MAC address"):
            unifi_reader.load_data()

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_validates_ip_addresses(
        self, mock_session_class: Mock, unifi_reader: UnifiReader
    ) -> None:
        """Test that UnifiReader validates IP address format."""
        from packages.ingest.readers.unifi import InvalidIPError

        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock responses with invalid IP
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"meta": {"rc": "ok"}}

        mock_devices_api_response = Mock()
        mock_devices_api_response.status_code = 200
        mock_devices_api_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "name": "Device",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "ip": "999.999.999.999",  # Invalid IP
                    "state": 1,
                }
            ],
        }

        mock_clients_api_response = Mock()
        mock_clients_api_response.status_code = 200
        mock_clients_api_response.json.return_value = {"meta": {"rc": "ok"}, "data": []}

        mock_session.post.side_effect = [
            mock_login_response,
            mock_devices_api_response,
            mock_clients_api_response,
        ]

        with pytest.raises(InvalidIPError, match="Invalid IP address"):
            unifi_reader.load_data()

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

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_returns_structured_data(
        self,
        mock_session_class: Mock,
        unifi_reader: UnifiReader,
        mock_devices_response: list[dict],
        mock_clients_response: list[dict],
    ) -> None:
        """Test that UnifiReader returns properly structured data."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock responses
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"meta": {"rc": "ok"}}

        mock_devices_api_response = Mock()
        mock_devices_api_response.status_code = 200
        mock_devices_api_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": mock_devices_response,
        }

        mock_clients_api_response = Mock()
        mock_clients_api_response.status_code = 200
        mock_clients_api_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": mock_clients_response,
        }

        mock_session.post.side_effect = [
            mock_login_response,
            mock_devices_api_response,
            mock_clients_api_response,
        ]

        result = unifi_reader.load_data()

        # Verify top-level structure
        assert isinstance(result, dict)
        assert "hosts" in result
        assert "ips" in result
        assert "relationships" in result

        # Verify hosts structure
        assert isinstance(result["hosts"], list)
        for host in result["hosts"]:
            assert "hostname" in host
            assert isinstance(host["hostname"], str)

        # Verify IPs structure
        assert isinstance(result["ips"], list)
        for ip in result["ips"]:
            assert "addr" in ip
            assert "ip_type" in ip
            assert "allocation" in ip
            assert ip["ip_type"] in ["v4", "v6"]

        # Verify relationships structure
        assert isinstance(result["relationships"], list)
        for rel in result["relationships"]:
            assert "type" in rel
            assert "source" in rel
            assert "target" in rel
            assert rel["type"] == "LOCATED_AT"

    @patch("packages.ingest.readers.unifi.requests.Session")
    def test_reader_handles_ipv6_addresses(
        self, mock_session_class: Mock, unifi_reader: UnifiReader
    ) -> None:
        """Test that UnifiReader handles IPv6 addresses."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock responses with IPv6
        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {"meta": {"rc": "ok"}}

        mock_devices_api_response = Mock()
        mock_devices_api_response.status_code = 200
        mock_devices_api_response.json.return_value = {
            "meta": {"rc": "ok"},
            "data": [
                {
                    "name": "Device-IPv6",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "ip": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                    "state": 1,
                }
            ],
        }

        mock_clients_api_response = Mock()
        mock_clients_api_response.status_code = 200
        mock_clients_api_response.json.return_value = {"meta": {"rc": "ok"}, "data": []}

        mock_session.post.side_effect = [
            mock_login_response,
            mock_devices_api_response,
            mock_clients_api_response,
        ]

        result = unifi_reader.load_data()

        # Verify IPv6 extraction
        ips = result["ips"]
        assert len(ips) == 1
        assert ips[0]["ip_type"] == "v6"
        assert ips[0]["addr"] == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
