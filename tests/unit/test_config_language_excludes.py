import re

from llamacrawl.config import (
    Config,
    FirecrawlSourceConfig,
    IngestionConfig,
    LanguageFilterConfig,
    SourceConfig,
    _apply_language_filter_to_firecrawl,
)


def _build_test_config(allowed_languages: list[str]) -> Config:
    """Create a minimal Config instance for testing language exclusions."""
    return Config(
        sources=SourceConfig(
            firecrawl=FirecrawlSourceConfig(
                exclude_paths=[],
                auto_exclude_non_allowed_languages=True,
            )
        ),
        ingestion=IngestionConfig(
            language_filter=LanguageFilterConfig(
                enabled=True,
                allowed_languages=allowed_languages,
            )
        ),
        # Required secret/URL fields (dummy but valid)
        firecrawl_api_url="https://firecrawl.example.com",
        firecrawl_api_key="fc-valid-test-key",
        tei_embedding_url="http://tei-embed.test",
        tei_reranker_url="http://tei-reranker.test",
    )


def test_auto_exclude_patterns_cover_common_language_paths() -> None:
    config = _build_test_config(allowed_languages=["en"])
    _apply_language_filter_to_firecrawl(config)

    patterns = config.sources.firecrawl.exclude_paths
    es_pattern = next(p for p in patterns if "es" in p)
    regex = re.compile(es_pattern, re.IGNORECASE)

    assert regex.search("/es/resources/page")
    assert regex.search("es/resources/page")
    assert regex.search("/es-mx/docs")
    assert not regex.search("/escapes/test")
    assert not regex.search("/escalate/path")


def test_auto_exclude_respects_feature_flag() -> None:
    config = _build_test_config(allowed_languages=["en"])
    config.sources.firecrawl.auto_exclude_non_allowed_languages = False
    _apply_language_filter_to_firecrawl(config)

    assert config.sources.firecrawl.exclude_paths == []
