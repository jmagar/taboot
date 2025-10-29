"""Tests for TEI configuration validation."""

import pytest
from pydantic import ValidationError

from packages.common.config import TabootConfig, TeiConfig


def test_tei_config_validates_batch_size_multiple_of_eight() -> None:
    cfg = TeiConfig(url="http://example.com", batch_size=32, timeout=60)
    assert cfg.batch_size == 32
    assert cfg.timeout == 60


def test_tei_config_rejects_non_multiple_batch_size() -> None:
    with pytest.raises(ValidationError):
        TeiConfig(url="http://example.com", batch_size=10, timeout=30)


def test_taboot_config_exposes_tei_config_block() -> None:
    config = TabootConfig(
        tei_embedding_url="http://localhost:4207",
        embedding_batch_size=32,
        tei_timeout=45,
    )

    tei = config.tei_config

    assert str(tei.url) == "http://localhost:4207"
    assert tei.batch_size == 32
    assert tei.timeout == 45
