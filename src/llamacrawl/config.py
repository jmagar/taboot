"""Configuration management for LlamaCrawl.

This module handles loading and validation of configuration from:
1. Environment variables (.env file) - for secrets and credentials
2. YAML configuration (config.yaml) - for pipeline settings

Configuration is loaded once at startup and validated using Pydantic v2.
Environment variables override YAML values where applicable.
"""

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Pydantic Configuration Models (Pydantic v2 syntax)
# =============================================================================


class FirecrawlLocationConfig(BaseModel):
    """Location targeting configuration for Firecrawl.

    Enables regional content filtering at the Firecrawl API level
    to reduce API credits spent on non-target regions.
    """

    country: str = Field(
        default="US",
        description="ISO 3166-1 alpha-2 country code (e.g., 'US', 'GB', 'FR')"
    )
    languages: list[str] = Field(
        default=["en-US"],
        description="Locale codes for language targeting (e.g., ['en-US', 'en-GB'])"
    )


class FirecrawlSourceConfig(BaseModel):
    """Firecrawl web scraping source configuration."""

    enabled: bool = True
    default_crawl_depth: int = Field(default=3, ge=1, le=10)
    max_pages: int = Field(default=1000, ge=1, le=10000)
    formats: list[str] = Field(default=["markdown"])
    urls: list[str] = Field(default_factory=list)
    include_paths: list[str] = Field(
        default_factory=list,
        description="URL path patterns to include (regex, e.g., ['^/en/', '^/docs/'])"
    )
    exclude_paths: list[str] = Field(
        default_factory=list,
        description="URL path patterns to exclude (regex, e.g., ['^/fr/', '^/de/']). Auto-populated from language_filter if empty."
    )
    location: FirecrawlLocationConfig | None = Field(
        default=None,
        description="Regional targeting configuration for Firecrawl API"
    )
    filter_non_english_metadata: bool = Field(
        default=True,
        description="Filter documents by Firecrawl's detected metadata.language field"
    )
    auto_exclude_non_allowed_languages: bool = Field(
        default=True,
        description="Automatically exclude language paths not in language_filter.allowed_languages"
    )
    concurrency: int | None = Field(default=None, ge=1, le=32)
    max_retries: int = Field(default=2, ge=0, le=10)
    retry_delay_ms: int = Field(default=2000, ge=0, le=60000)
    timeout_ms: int | None = Field(default=None, ge=0, le=120000)


class GitHubSourceConfig(BaseModel):
    """GitHub repositories source configuration."""

    enabled: bool = True
    repositories: list[str] = Field(
        default_factory=list,
        description=(
            "List of repository identifiers. Accepts either 'owner/repo' or bare 'owner' entries; "
            "bare owners expand to all accessible repositories for that owner."
        ),
    )
    include_issues: bool = True
    include_prs: bool = True
    # Note: include_discussions removed - GitHub Discussions API not implemented
    file_extensions: list[str] = Field(
        default=[".md", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"]
    )

    @field_validator("repositories")
    @classmethod
    def validate_repositories(cls, v: list[str]) -> list[str]:
        """Validate repository entries, allowing owner or owner/repo formats."""
        cleaned: list[str] = []
        for repo in v:
            repo_identifier = repo.strip()
            if not repo_identifier:
                raise ValueError("Repository entries cannot be empty")

            if repo_identifier.count("/") > 1:
                raise ValueError(
                    f"Invalid repository format: {repo_identifier}. "
                    "Expected 'owner/repo' or 'owner'"
                )

            if "/" in repo_identifier:
                owner, repo_name = repo_identifier.split("/", 1)
                if not owner or not repo_name:
                    raise ValueError(
                        f"Invalid repository format: {repo_identifier}. "
                        "Expected 'owner/repo'"
                    )

            cleaned.append(repo_identifier)
        return cleaned


class RedditSourceConfig(BaseModel):
    """Reddit posts and comments source configuration."""

    enabled: bool = True
    subreddits: list[str] = Field(default_factory=list)
    post_limit: int = Field(default=1000, ge=1, le=1000)
    include_comments: bool = True
    max_comment_depth: int = Field(default=5, ge=1, le=10)


class ElasticsearchSourceConfig(BaseModel):
    """Elasticsearch document store source configuration."""

    enabled: bool = False
    indices: list[str] = Field(default_factory=list)
    field_mappings: dict[str, str] = Field(
        default={"title": "title", "content": "content", "timestamp": "@timestamp"}
    )
    query_filter: dict[str, Any] = Field(default_factory=dict)
    batch_size: int = Field(default=200, ge=1, le=1000)


class GmailSourceConfig(BaseModel):
    """Gmail email messages source configuration."""

    enabled: bool = False
    labels: list[str] = Field(default=["INBOX", "SENT"])
    include_attachments_metadata: bool = True
    query_filters: list[str] = Field(default_factory=list)


class SourceConfig(BaseModel):
    """Configuration for all data sources."""

    firecrawl: FirecrawlSourceConfig = Field(default_factory=FirecrawlSourceConfig)
    github: GitHubSourceConfig = Field(default_factory=GitHubSourceConfig)
    reddit: RedditSourceConfig = Field(default_factory=RedditSourceConfig)
    elasticsearch: ElasticsearchSourceConfig = Field(default_factory=ElasticsearchSourceConfig)
    gmail: GmailSourceConfig = Field(default_factory=GmailSourceConfig)


class RetryConfig(BaseModel):
    """Retry logic configuration."""

    max_attempts: int = Field(default=5, ge=1, le=10)
    initial_delay_seconds: float = Field(default=1.0, ge=0.1, le=60.0)
    max_delay_seconds: float = Field(default=60.0, ge=1.0, le=600.0)
    jitter: float = Field(default=0.2, ge=0.0, le=1.0)


class DeduplicationConfig(BaseModel):
    """Deduplication strategy configuration.

    Deduplication is always enabled and uses content hash strategy.
    """

    # Deduplication is always enabled, no config needed
    # Strategy is always 'hash' (SHA-256 content hashing)
    # normalize_whitespace: Normalize whitespace before hashing
    normalize_whitespace: bool = True
    # remove_punctuation: Remove punctuation before hashing
    remove_punctuation: bool = False
    # normalize_case: Normalize case (lowercase) before hashing
    normalize_case: bool = False


class DLQConfig(BaseModel):
    """Dead Letter Queue configuration."""

    enabled: bool = True
    retention_days: int = Field(default=7, ge=1, le=30)


class LanguageFilterConfig(BaseModel):
    """Language filtering configuration for pipeline.

    Controls content-based language filtering that happens BEFORE embedding
    to save compute costs and storage space on non-target language content.
    """

    enabled: bool = Field(
        default=True,
        description="Enable language filtering in ingestion pipeline"
    )
    allowed_languages: list[str] = Field(
        default=["en"],
        description="List of ISO 639-1 language codes to keep (e.g., ['en', 'es'])"
    )
    confidence_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum detection confidence (0.0-1.0)"
    )
    min_content_length: int = Field(
        default=50,
        ge=0,
        description="Minimum text length for detection (shorter text passes through)"
    )
    log_filtered: bool = Field(
        default=True,
        description="Log detailed filtering statistics"
    )


class IngestionConfig(BaseModel):
    """Ingestion pipeline configuration.

    Note: chunk_size increased to support Qwen3-Embedding-0.6B's 32K context window.
    Recommended: 8192 tokens (official Qwen3 examples use this value)
    Maximum: 32768 tokens (model's native limit)
    """

    chunk_size: int = Field(default=512, ge=128, le=32768)  # Support full Qwen3 32K context
    chunk_overlap: int = Field(default=50, ge=0, le=8192)   # Allow up to 25% overlap at 32K chunks
    batch_size: int = Field(default=32, ge=1, le=1000)
    pipeline_workers: int = Field(default=1, ge=1, le=32)
    embedding_batch_size: int = Field(default=64, ge=1, le=256)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    deduplication: DeduplicationConfig = Field(default_factory=DeduplicationConfig)
    dlq: DLQConfig = Field(default_factory=DLQConfig)
    language_filter: LanguageFilterConfig = Field(
        default_factory=LanguageFilterConfig,
        description="Language filtering configuration (filters BEFORE embedding)"
    )


class QueryConfig(BaseModel):
    """Query pipeline configuration."""

    top_k: int = Field(default=20, ge=1, le=100)
    rerank_top_n: int = Field(default=5, ge=1, le=50)
    enable_reranking: bool = True
    enable_graph_traversal: bool = True
    max_graph_depth: int = Field(default=2, ge=1, le=5)
    synthesis_model: str = "claude-3-5-haiku-20241022"  # Fast and cheap for RAG synthesis
    max_input_tokens: int = Field(default=4096, ge=512, le=200000)  # Claude supports up to 200K
    # Note: temperature removed - Claude SDK doesn't support it in this context
    include_snippets: bool = True
    snippet_length: int = Field(default=200, ge=50, le=1000)


class GraphConfig(BaseModel):
    """Knowledge graph extraction configuration."""

    auto_extract_entities: bool = True
    extraction_model: str = "claude-3-5-haiku-20241022"  # Fast/cheap Claude model for extraction
    # Note: max_keywords_per_document removed - not used in implementation
    # Note: relationship_extraction removed - always enabled, not toggleable
    entity_types: list[str] = Field(
        default=["PERSON", "ORGANIZATION", "LOCATION", "PRODUCT", "TECHNOLOGY", "EVENT", "FILE", "CONCEPT"]
    )
    extraction_strategy: Literal["simple", "implicit", "schema", "combined"] = "simple"
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_triplets_per_chunk: int = Field(default=30, ge=1, le=100)
    include_implicit_relations: bool = True

    # Entity type schemas with properties
    entity_properties: dict[str, list[str]] = Field(
        default={
            "PERSON": ["email", "role", "title", "company"],
            "ORGANIZATION": ["industry", "size", "website", "location"],
            "LOCATION": ["address", "coordinates", "type"],
            "PRODUCT": ["version", "vendor", "category"],
            "TECHNOLOGY": ["language", "framework", "version"],
            "EVENT": ["startTime", "endTime", "location", "type"],
            "FILE": ["fileId", "source", "format", "lastModified"],
            "CONCEPT": ["category", "domain", "relatedTo"],
        }
    )

    # Relation type schemas with properties
    relation_types: list[str] = Field(
        default=[
            "WORKS_FOR", "CREATED_BY", "LOCATED_IN", "USES", "PART_OF",
            "RELATED_TO", "IMPLEMENTS", "DEPENDS_ON", "MENTIONS", "REFERENCES"
        ]
    )

    relation_properties: dict[str, list[str]] = Field(
        default={
            "WORKS_FOR": ["role", "startDate", "endDate"],
            "CREATED_BY": ["date", "version"],
            "LOCATED_IN": ["since", "type"],
            "USES": ["purpose", "frequency"],
            "PART_OF": ["role", "percentage"],
            "RELATED_TO": ["strength", "type"],
            "IMPLEMENTS": ["version", "standard"],
            "DEPENDS_ON": ["version", "type"],
            "MENTIONS": ["context", "sentiment"],
            "REFERENCES": ["page", "section"],
        }
    )

    allowed_entity_types: list[str] | None = None
    allowed_relation_types: list[str] | None = None


class HNSWConfig(BaseModel):
    """HNSW index parameters for Qdrant."""

    m: int = Field(default=16, ge=4, le=64)
    ef_construct: int = Field(default=100, ge=10, le=1000)


class VectorStoreConfig(BaseModel):
    """Vector store configuration."""

    collection_name: str = "llamacrawl_documents"
    vector_dimension: int = Field(default=1024, ge=384, le=4096)
    distance_metric: Literal["cosine", "euclidean", "dot"] = "cosine"
    enable_quantization: bool = True
    hnsw: HNSWConfig = Field(default_factory=HNSWConfig)
    upsert_batch_size: int = Field(default=256, ge=1, le=1024)
    upsert_parallel: int = Field(default=4, ge=1, le=16)
    upsert_max_retries: int = Field(default=3, ge=0, le=10)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    format: Literal["json", "text"] = "json"
    level: str = "INFO"
    log_sensitive_data: bool = False


class MetricsConfig(BaseModel):
    """Metrics configuration.

    NOTE: Metrics collection is not yet implemented. This is a placeholder config.
    """

    # All metrics options are placeholders - not used in current implementation
    enabled: bool = False  # Changed to False since not implemented


class Config(BaseModel):
    """Root configuration model combining all settings.

    This model contains all configuration loaded from config.yaml
    and overridden by environment variables where applicable.
    """

    # Data sources
    sources: SourceConfig = Field(default_factory=SourceConfig)

    # Pipeline settings
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    query: QueryConfig = Field(default_factory=QueryConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)

    # Observability
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    # Environment variables (secrets and URLs)
    # Data source credentials
    firecrawl_api_url: str
    firecrawl_api_key: str
    github_token: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "LlamaCrawl/1.0"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_oauth_refresh_token: str | None = None
    elasticsearch_url: str | None = None
    elasticsearch_api_key: str | None = None

    # Infrastructure URLs
    qdrant_url: str = "http://localhost:7000"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"
    redis_url: str = "redis://localhost:6379"
    tei_embedding_url: str
    tei_reranker_url: str

    # Observability (env var overrides)
    log_level: str = "INFO"
    prometheus_port: int = 9090

    @field_validator("firecrawl_api_key")
    @classmethod
    def validate_firecrawl_api_key(cls, v: str) -> str:
        """Validate Firecrawl API key format."""
        if not v or v.startswith("fc-xxx"):
            raise ValueError(
                "Invalid FIRECRAWL_API_KEY. Please set a valid API key in .env file. "
                "Get your API key from your Firecrawl instance admin panel."
            )
        return v

    @field_validator("github_token")
    @classmethod
    def validate_github_token(cls, v: str | None) -> str | None:
        """Validate GitHub token if provided."""
        if v and v.startswith("ghp_xxx"):
            raise ValueError(
                "Invalid GITHUB_TOKEN. Please set a valid Personal Access Token in .env file. "
                "Create one at https://github.com/settings/tokens"
            )
        return v


# =============================================================================
# Configuration Loading Functions
# =============================================================================


def load_config(
    env_file: Path | str = ".env", config_file: Path | str = "config.yaml"
) -> Config:
    """Load and validate configuration from .env and config.yaml files.

    This function:
    1. Loads environment variables from .env file
    2. Loads YAML configuration from config.yaml
    3. Merges environment variables (which override YAML values)
    4. Validates all configuration using Pydantic
    5. Fails fast if required values are missing

    Args:
        env_file: Path to .env file (default: .env)
        config_file: Path to config.yaml file (default: config.yaml)

    Returns:
        Validated Config object with all settings

    Raises:
        FileNotFoundError: If config files are missing
        ValueError: If configuration validation fails
        yaml.YAMLError: If YAML parsing fails
    """
    # Convert to Path objects
    env_path = Path(env_file)
    config_path = Path(config_file)

    # Load environment variables
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        raise FileNotFoundError(
            f"Environment file not found: {env_path}. "
            f"Copy .env.example to .env and fill in your credentials."
        )

    # Load YAML configuration
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}. "
            f"Copy config.example.yaml to config.yaml and adjust settings."
        )

    with open(config_path) as f:
        try:
            yaml_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML configuration: {e}") from e

    # Merge environment variables with YAML config
    # Environment variables override YAML values
    config_data = {
        **yaml_config,
        # Data source credentials (required)
        "firecrawl_api_url": os.getenv("FIRECRAWL_API_URL", "https://firecrawl.tootie.tv"),
        "firecrawl_api_key": os.getenv("FIRECRAWL_API_KEY", ""),
        # GitHub (optional)
        "github_token": os.getenv("GITHUB_TOKEN"),
        # Reddit (optional)
        "reddit_client_id": os.getenv("REDDIT_CLIENT_ID"),
        "reddit_client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
        "reddit_user_agent": os.getenv("REDDIT_USER_AGENT", "LlamaCrawl/1.0"),
        # Gmail (optional)
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "google_client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "google_oauth_refresh_token": os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN"),
        # Elasticsearch (optional)
        "elasticsearch_url": os.getenv("ELASTICSEARCH_URL"),
        "elasticsearch_api_key": os.getenv("ELASTICSEARCH_API_KEY"),
        # Infrastructure URLs (with defaults)
        "qdrant_url": os.getenv("QDRANT_URL", "http://localhost:7000"),
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD", "changeme"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "tei_embedding_url": os.getenv("TEI_EMBEDDING_URL"),
        "tei_reranker_url": os.getenv("TEI_RERANKER_URL"),
        # Observability (override YAML if env var set)
        "log_level": os.getenv("LOG_LEVEL", yaml_config.get("logging", {}).get("level", "INFO")),
        "prometheus_port": int(
            os.getenv(
                "PROMETHEUS_PORT",
                str(yaml_config.get("metrics", {}).get("prometheus_port", 9090)),
            )
        ),
    }

    # Validate and create Config object
    try:
        config = Config(**config_data)
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}") from e

    # Validate required infrastructure URLs
    if not config.tei_embedding_url:
        raise ValueError("TEI_EMBEDDING_URL environment variable is required")
    if not config.tei_reranker_url:
        raise ValueError("TEI_RERANKER_URL environment variable is required")

    # Additional validation: check enabled sources have credentials
    _validate_source_credentials(config)

    # Auto-populate Firecrawl exclude_paths from language_filter if enabled
    _apply_language_filter_to_firecrawl(config)

    return config


def _validate_source_credentials(config: Config) -> None:
    """Validate that enabled sources have required credentials.

    Args:
        config: Config object to validate

    Raises:
        ValueError: If enabled source is missing required credentials
    """
    errors = []

    # GitHub requires token
    if config.sources.github.enabled and not config.github_token:
        errors.append(
            "GitHub is enabled but GITHUB_TOKEN is not set. "
            "Set GITHUB_TOKEN in .env or disable GitHub in config.yaml"
        )

    # Reddit requires client credentials
    if (
        config.sources.reddit.enabled
        and (not config.reddit_client_id or not config.reddit_client_secret)
    ):
        errors.append(
            "Reddit is enabled but REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET is not set. "
            "Set credentials in .env or disable Reddit in config.yaml"
        )

    # Gmail requires OAuth credentials
    if config.sources.gmail.enabled:
        if not config.google_client_id or not config.google_client_secret:
            errors.append(
                "Gmail is enabled but GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is not set. "
                "Set credentials in .env or disable Gmail in config.yaml"
            )
        if not config.google_oauth_refresh_token:
            errors.append(
                "Gmail is enabled but GOOGLE_OAUTH_REFRESH_TOKEN is not set. "
                "Run OAuth flow to obtain refresh token or disable Gmail in config.yaml"
            )

    # Elasticsearch requires URL and API key
    if config.sources.elasticsearch.enabled:
        if not config.elasticsearch_url:
            errors.append(
                "Elasticsearch is enabled but ELASTICSEARCH_URL is not set. "
                "Set URL in .env or disable Elasticsearch in config.yaml"
            )
        if not config.elasticsearch_api_key:
            errors.append(
                "Elasticsearch is enabled but ELASTICSEARCH_API_KEY is not set. "
                "Set API key in .env or disable Elasticsearch in config.yaml"
            )

    if errors:
        error_list = "\n".join(f"  - {e}" for e in errors)
        raise ValueError(
            f"Missing required credentials for enabled sources:\n{error_list}"
        )


def _apply_language_filter_to_firecrawl(config: Config) -> None:
    """Auto-populate Firecrawl exclude_paths from language_filter config.

    If language_filter is enabled and auto_exclude_non_allowed_languages is True,
    this generates URL path exclusion patterns for all common language codes
    NOT in the allowed_languages list.

    This makes language_filter.allowed_languages the single source of truth
    for language filtering across all layers.

    Args:
        config: Config object to modify
    """
    if not config.ingestion.language_filter.enabled:
        return

    if not config.sources.firecrawl.auto_exclude_non_allowed_languages:
        return

    # Common ISO 639-1 language codes used in URLs
    # Format: language code -> common URL patterns
    common_language_paths = {
        "de", "fr", "es", "ja", "zh", "pt", "ru", "ko", "it", "nl",
        "pl", "tr", "vi", "th", "sv", "da", "fi", "no", "cs", "ro",
        "hu", "el", "he", "id", "ms", "uk", "bg", "ar", "hi", "bn",
    }

    # Get allowed languages
    allowed = set(lang.lower() for lang in config.ingestion.language_filter.allowed_languages)

    # Calculate which languages to exclude
    languages_to_exclude = common_language_paths - allowed

    if not languages_to_exclude:
        # No languages to exclude (all allowed or allowed_languages is empty)
        return

    # Generate exclude patterns
    # Firecrawl expects regex patterns that match the request path without the leading slash.
    # Use a pattern that tolerates optional leading slash and locale suffixes (e.g., es-MX/).
    auto_exclude_patterns = [
        rf"^(?:/)?{lang}(?:[-_][a-z0-9]+)?(?:/|$)" for lang in sorted(languages_to_exclude)
    ]

    # Add to existing exclude_paths (avoid duplicates)
    existing_patterns = set(config.sources.firecrawl.exclude_paths)
    new_patterns = [p for p in auto_exclude_patterns if p not in existing_patterns]

    if new_patterns:
        config.sources.firecrawl.exclude_paths.extend(new_patterns)
        from llamacrawl.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info(
            f"Auto-generated {len(new_patterns)} language path exclusions from language_filter",
            extra={
                "allowed_languages": sorted(allowed),
                "excluded_language_paths": sorted(languages_to_exclude),
                "total_exclude_paths": len(config.sources.firecrawl.exclude_paths),
            }
        )


# =============================================================================
# Global Configuration Singleton
# =============================================================================

# Global config instance (initialized on first import)
# This is loaded once and reused throughout the application
_config: Config | None = None


def get_config(reload: bool = False) -> Config:
    """Get global configuration singleton.

    Args:
        reload: If True, force reload configuration from files (default: False)

    Returns:
        Global Config instance

    Example:
        >>> config = get_config()
        >>> print(config.sources.github.enabled)
        True
    """
    global _config

    if _config is None or reload:
        _config = load_config()

    return _config


# Convenience alias for backward compatibility
config = get_config()
