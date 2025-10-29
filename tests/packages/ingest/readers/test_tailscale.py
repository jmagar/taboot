"""Tests for TailscaleReader.

Tests Tailscale API client following TDD methodology (RED-GREEN-REFACTOR).
Extracts Host nodes, IP nodes, and LOCATED_AT relationships.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest


class TestTailscaleReader:
    """Tests for the TailscaleReader class."""

    @pytest.fixture
    def sample_devices_response(self) -> dict[str, Any]:
        """Create a sample Tailscale API devices response for testing.

        Returns:
            dict[str, Any]: Mock API response with device data.
        """
        return {
            "devices": [
                {
                    "id": "device1",
                    "hostname": "server01",
                    "addresses": ["100.64.1.10", "fd7a:115c:a1e0::1"],
                    "os": "linux",
                    "name": "server01.example.com",
                },
                {
                    "id": "device2",
                    "hostname": "workstation",
                    "addresses": ["100.64.1.20"],
                    "os": "darwin",
                    "name": "workstation.example.com",
                },
            ]
        }

    @pytest.fixture
    def minimal_devices_response(self) -> dict[str, Any]:
        """Create a minimal Tailscale API response with single device.

        Returns:
            dict[str, Any]: Mock API response with minimal device data.
        """
        return {
            "devices": [
                {
                    "id": "device1",
                    "hostname": "minimal",
                    "addresses": ["100.64.1.1"],
                    "os": "linux",
                    "name": "minimal.example.com",
                }
            ]
        }

    @pytest.fixture
    def empty_devices_response(self) -> dict[str, Any]:
        """Create an empty Tailscale API response.

        Returns:
            dict[str, Any]: Mock API response with no devices.
        """
        return {"devices": []}

    @patch("requests.get")
    def test_reader_extracts_hosts(
        self, mock_get: Mock, sample_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader extracts Host nodes."""
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = sample_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        # Should extract 2 hosts: server01, workstation
        assert "hosts" in result
        hosts = result["hosts"]
        assert len(hosts) == 2

        # Verify host names
        host_names = {host["hostname"] for host in hosts}
        assert host_names == {"server01", "workstation"}

    @patch("requests.get")
    def test_reader_extracts_ip_addresses(
        self, mock_get: Mock, sample_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader extracts IP nodes."""
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = sample_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        # Should extract 3 IP addresses: 100.64.1.10, fd7a:115c:a1e0::1, 100.64.1.20
        assert "ips" in result
        ips = result["ips"]
        assert len(ips) == 3

        # Verify IP addresses
        ip_addrs = {ip["addr"] for ip in ips}
        assert ip_addrs == {"100.64.1.10", "fd7a:115c:a1e0::1", "100.64.1.20"}

    @patch("requests.get")
    def test_reader_determines_ip_type(
        self, mock_get: Mock, sample_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader correctly identifies IPv4 vs IPv6."""
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = sample_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        ips = {ip["addr"]: ip for ip in result["ips"]}

        # IPv4 addresses
        assert ips["100.64.1.10"]["ip_type"] == "v4"
        assert ips["100.64.1.20"]["ip_type"] == "v4"

        # IPv6 address
        assert ips["fd7a:115c:a1e0::1"]["ip_type"] == "v6"

    @patch("requests.get")
    def test_reader_extracts_located_at_relationships(
        self, mock_get: Mock, sample_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader extracts LOCATED_AT relationships."""
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = sample_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        assert "relationships" in result
        relationships = result["relationships"]

        # Filter LOCATED_AT relationships
        located_at = [r for r in relationships if r["type"] == "LOCATED_AT"]

        # server01 has 2 IPs, workstation has 1 IP = 3 total relationships
        assert len(located_at) == 3

        # Verify specific relationships
        server01_rels = [r for r in located_at if r["source"] == "server01"]
        assert len(server01_rels) == 2
        server01_targets = {r["target"] for r in server01_rels}
        assert server01_targets == {"100.64.1.10", "fd7a:115c:a1e0::1"}

        workstation_rels = [r for r in located_at if r["source"] == "workstation"]
        assert len(workstation_rels) == 1
        assert workstation_rels[0]["target"] == "100.64.1.20"

    @patch("requests.get")
    def test_reader_requires_api_key(self, mock_get: Mock) -> None:
        """Test that TailscaleReader requires API key."""
        from packages.ingest.readers.tailscale import TailscaleReader

        with pytest.raises(ValueError, match="api_key cannot be empty"):
            TailscaleReader(api_key="", tailnet="example.com")

    @patch("requests.get")
    def test_reader_requires_tailnet(self, mock_get: Mock) -> None:
        """Test that TailscaleReader requires tailnet."""
        from packages.ingest.readers.tailscale import TailscaleReader

        with pytest.raises(ValueError, match="tailnet cannot be empty"):
            TailscaleReader(api_key="test-key", tailnet="")

    @patch("requests.get")
    def test_reader_handles_api_auth_failure(self, mock_get: Mock) -> None:
        """Test that TailscaleReader raises error for auth failures."""
        from packages.ingest.readers.tailscale import TailscaleAPIError, TailscaleReader

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="invalid-key", tailnet="example.com")

        with pytest.raises(TailscaleAPIError, match="Failed to fetch devices"):
            reader.load_data()

    @patch("requests.get")
    def test_reader_handles_network_errors(self, mock_get: Mock) -> None:
        """Test that TailscaleReader raises error for network failures."""
        from packages.ingest.readers.tailscale import TailscaleAPIError, TailscaleReader

        mock_get.side_effect = Exception("Network error")

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")

        with pytest.raises(TailscaleAPIError, match="Failed to fetch devices"):
            reader.load_data()

    @patch("requests.get")
    def test_reader_handles_empty_devices(
        self, mock_get: Mock, empty_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader handles empty device list."""
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = empty_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        assert result["hosts"] == []
        assert result["ips"] == []
        assert result["relationships"] == []

    @patch("requests.get")
    def test_reader_validates_ip_addresses(self, mock_get: Mock) -> None:
        """Test that TailscaleReader validates IP address formats."""
        from packages.ingest.readers.tailscale import InvalidIPError, TailscaleReader

        invalid_response = {
            "devices": [
                {
                    "id": "device1",
                    "hostname": "invalid",
                    "addresses": ["999.999.999.999"],  # Invalid IPv4
                    "os": "linux",
                    "name": "invalid.example.com",
                }
            ]
        }

        mock_response = Mock()
        mock_response.json.return_value = invalid_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")

        with pytest.raises(InvalidIPError, match="Invalid IP address"):
            reader.load_data()

    @patch("requests.get")
    def test_reader_returns_structured_data(
        self, mock_get: Mock, sample_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader returns properly structured data."""
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = sample_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

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

        # Verify ips structure
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

    @patch("requests.get")
    def test_reader_includes_api_key_in_header(
        self, mock_get: Mock, sample_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader includes API key in Authorization header."""
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = sample_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key-123", tailnet="example.com")
        reader.load_data()

        # Verify API call was made with correct headers
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-key-123"

    @patch("requests.get")
    def test_reader_constructs_correct_api_url(
        self, mock_get: Mock, sample_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader constructs correct API URL."""
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = sample_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        reader.load_data()

        # Verify API URL
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.tailscale.com/api/v2/tailnet/example.com/devices"

    @patch("requests.get")
    def test_reader_sets_static_allocation(
        self, mock_get: Mock, sample_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader sets allocation to static for Tailscale IPs."""
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = sample_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        # All Tailscale IPs should be marked as static
        for ip in result["ips"]:
            assert ip["allocation"] == "static"

    @patch("requests.get")
    def test_reader_handles_device_without_addresses(self, mock_get: Mock) -> None:
        """Test that TailscaleReader handles devices without addresses."""
        from packages.ingest.readers.tailscale import TailscaleReader

        response = {
            "devices": [
                {
                    "id": "device1",
                    "hostname": "no-addr",
                    "addresses": [],
                    "os": "linux",
                    "name": "no-addr.example.com",
                }
            ]
        }

        mock_response = Mock()
        mock_response.json.return_value = response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        # Should still extract host
        assert len(result["hosts"]) == 1
        assert result["hosts"][0]["hostname"] == "no-addr"

        # But no IPs or relationships
        assert len(result["ips"]) == 0
        assert len(result["relationships"]) == 0


class TestTailscaleReaderNewEntities:
    """Integration tests for TailscaleReader with new entity types.

    Tests conversion to TailscaleDevice, TailscaleNetwork, TailscaleACL schemas
    following the Phase 4 refactor requirements (T210-T212).
    """

    @pytest.fixture
    def comprehensive_devices_response(self) -> dict[str, Any]:
        """Create comprehensive Tailscale API response with all fields.

        Returns:
            dict[str, Any]: Mock API response with full device data including
                           exit nodes, ACLs, subnet routes, and SSH configuration.
        """
        return {
            "devices": [
                {
                    "id": "device-123",
                    "hostname": "gateway.example.com",
                    "addresses": ["100.64.1.5", "fd7a:115c:a1e0::1"],
                    "os": "linux",
                    "name": "gateway.example.com",
                    "endpoints": ["192.168.1.100:41641", "203.0.113.50:41641"],
                    "keyExpiryDisabled": False,
                    "isExitNode": True,
                    "advertiseRoutes": ["10.0.0.0/24", "10.1.0.0/24"],
                    "enabledSSH": True,
                    "tailnetDNSName": "gateway.tailnet-abc.ts.net",
                    "lastSeen": "2024-01-15T09:00:00Z",
                },
                {
                    "id": "device-456",
                    "hostname": "workstation.local",
                    "addresses": ["100.64.2.10"],
                    "os": "darwin",
                    "name": "workstation.local",
                    "dnsName": "workstation.tailnet-abc.ts.net",
                    "endpoints": ["192.168.1.200:41641"],
                    "keyExpiryDisabled": False,
                    "isExitNode": False,
                    "enabledSSH": False,
                    "lastSeen": "2024-01-15T10:00:00Z",
                },
            ]
        }

    @patch("requests.get")
    def test_reader_outputs_tailscale_device_entities(
        self, mock_get: Mock, comprehensive_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader outputs TailscaleDevice entities."""
        from packages.ingest.readers.tailscale import TailscaleReader
        from packages.schemas.tailscale import TailscaleDevice

        mock_response = Mock()
        mock_response.json.return_value = comprehensive_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        # Should have devices key with TailscaleDevice entities
        assert "devices" in result
        devices = result["devices"]
        assert len(devices) == 2

        # Validate first device (gateway)
        gateway = devices[0]
        assert isinstance(gateway, TailscaleDevice)
        assert gateway.device_id == "device-123"
        assert gateway.hostname == "gateway.example.com"
        assert gateway.long_domain == "gateway.example.com"
        assert gateway.os == "linux"
        assert gateway.ipv4_address == "100.64.1.5"
        assert gateway.ipv6_address == "fd7a:115c:a1e0::1"
        assert gateway.endpoints == ["192.168.1.100:41641", "203.0.113.50:41641"]
        assert gateway.is_exit_node is True
        assert gateway.subnet_routes == ["10.0.0.0/24", "10.1.0.0/24"]
        assert gateway.ssh_enabled is True
        assert gateway.tailnet_dns_name == "gateway.tailnet-abc.ts.net"

        # Validate temporal and extraction metadata
        assert gateway.created_at is not None
        assert gateway.updated_at is not None
        assert gateway.source_timestamp is not None
        assert gateway.extraction_tier == "A"
        assert gateway.extraction_method == "tailscale_api"
        assert gateway.confidence == 1.0
        assert gateway.extractor_version is not None

        # Validate second device (workstation)
        workstation = devices[1]
        assert isinstance(workstation, TailscaleDevice)
        assert workstation.device_id == "device-456"
        assert workstation.hostname == "workstation.local"
        assert workstation.long_domain == "workstation.local"
        assert workstation.os == "darwin"
        assert workstation.ipv4_address == "100.64.2.10"
        assert workstation.ipv6_address is None
        assert workstation.is_exit_node is False
        assert workstation.ssh_enabled is False
        assert workstation.tailnet_dns_name == "workstation.tailnet-abc.ts.net"

    @patch("requests.get")
    def test_reader_outputs_tailscale_network_entities(
        self, mock_get: Mock, comprehensive_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader outputs TailscaleNetwork entities.

        Note: This requires extracting network configuration from the Tailscale API,
        which may be inferred from device subnet routes or require additional API calls.
        """
        from packages.ingest.readers.tailscale import TailscaleReader
        from packages.schemas.tailscale import TailscaleNetwork

        mock_response = Mock()
        mock_response.json.return_value = comprehensive_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        # Should have networks key with TailscaleNetwork entities
        assert "networks" in result
        networks = result["networks"]

        # At minimum, should extract subnet routes as networks
        if len(networks) > 0:
            network = networks[0]
            assert isinstance(network, TailscaleNetwork)
            assert network.network_id is not None
            assert network.name is not None
            assert network.cidr is not None
            assert network.created_at is not None
            assert network.updated_at is not None
            assert network.extraction_tier == "A"
            assert network.extraction_method == "tailscale_api"
            assert network.confidence == 1.0

    @patch("requests.get")
    def test_reader_outputs_tailscale_acl_entities(
        self, mock_get: Mock, comprehensive_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader outputs TailscaleACL entities.

        Note: ACL extraction requires additional API calls to fetch ACL policy.
        This test may be skipped if ACL extraction is not implemented in Phase 4.
        """
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = comprehensive_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        # Should have acls key (may be empty if ACL extraction not yet implemented)
        assert "acls" in result
        # ACL extraction implementation is optional for Phase 4
        # We just verify the structure exists

    @patch("requests.get")
    def test_reader_maintains_backward_compatibility(
        self, mock_get: Mock, comprehensive_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader maintains backward compatibility during migration.

        During the migration period, the reader should output both old and new formats
        to avoid breaking existing consumers.
        """
        from packages.ingest.readers.tailscale import TailscaleReader

        mock_response = Mock()
        mock_response.json.return_value = comprehensive_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        # New format (Phase 4)
        assert "devices" in result
        assert "networks" in result
        assert "acls" in result

        # Old format (maintained for backward compatibility)
        assert "hosts" in result
        assert "ips" in result
        assert "relationships" in result

    @patch("requests.get")
    def test_reader_validates_new_entity_schemas(
        self, mock_get: Mock, comprehensive_devices_response: dict[str, Any]
    ) -> None:
        """Test that TailscaleReader validates entities against Pydantic schemas."""
        from packages.ingest.readers.tailscale import TailscaleReader
        from packages.schemas.tailscale import TailscaleDevice

        mock_response = Mock()
        mock_response.json.return_value = comprehensive_devices_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        reader = TailscaleReader(api_key="test-key", tailnet="example.com")
        result = reader.load_data()

        # All devices should pass Pydantic validation
        for device in result["devices"]:
            assert isinstance(device, TailscaleDevice)
            # Re-validate using Pydantic's model_validate
            TailscaleDevice.model_validate(device.model_dump())
