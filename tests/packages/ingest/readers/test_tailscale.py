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
