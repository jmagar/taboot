"""Configuration management for Taboot platform.

Loads environment variables using pydantic-settings for type-safe configuration.
All service URLs, credentials, and tuning parameters are defined here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class TabootConfig(BaseSettings):
    """Main configuration class for Taboot platform.

    Loads all service URLs, credentials, and tuning parameters from environment variables.
    Uses pydantic-settings for validation and type safety.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========== Service URLs ==========
    firecrawl_api_url: str = "http://taboot-crawler:3002"
    redis_url: str = "redis://taboot-cache:6379"
    qdrant_url: str = "http://taboot-vectors:6333"
    neo4j_uri: str = "bolt://taboot-graph:7687"
    tei_embedding_url: str = "http://taboot-embed:80"
    reranker_url: str = "http://taboot-rerank:8000"
    playwright_microservice_url: str = "http://taboot-playwright:3000/scrape"

    # ========== Database Credentials ==========
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"
    neo4j_db: str = "neo4j"

    postgres_user: str = "taboot"
    postgres_password: str = "changeme"
    postgres_db: str = "taboot"
    postgres_port: int = 5432

    # ========== Vector & Embedding Config ==========
    collection_name: str = "documents"
    tei_embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    qdrant_embedding_dim: int = 768

    # ========== Reranker Config ==========
    reranker_model: str = "Qwen/Qwen3-Reranker-0.6B"
    reranker_batch_size: int = 16
    reranker_device: str = "auto"  # "auto", "cuda", or "cpu"

    # ========== Ollama LLM Config ==========
    ollama_port: int = 11434
    ollama_flash_attention: bool = True
    ollama_keep_alive: str = "30m"
    ollama_use_mmap: bool = True
    ollama_max_queue: int = 20000

    # ========== Extraction Pipeline Tuning ==========
    tier_c_batch_size: int = 16  # LLM batch size (8-16 optimal per research.md)
    tier_c_workers: int = 4  # Concurrent LLM workers
    redis_cache_ttl: int = 604800  # 7 days in seconds
    neo4j_batch_size: int = 2000  # UNWIND batch size (2k rows optimal)

    # ========== Ingestion Tuning ==========
    crawl_concurrency: int = 5  # Concurrent crawling requests
    embedding_batch_size: int = 32  # TEI embedding batch size

    # ========== External API Credentials (Optional) ==========
    github_token: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "Script"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_oauth_refresh_token: str | None = None
    elasticsearch_url: str | None = None
    elasticsearch_api_key: str | None = None
    tailscale_api_key: str | None = None
    unifi_username: str | None = None
    unifi_password: str | None = None
    unifi_api_token: str | None = None

    # ========== Firecrawl Config ==========
    firecrawl_api_key: str = "changeme"
    num_workers_per_queue: int = 16
    worker_concurrency: int = 8
    scrape_concurrency: int = 8
    retry_delay: int = 1000
    max_retries: int = 1

    # ========== Observability ==========
    log_level: str = "INFO"

    # ========== API Service ==========
    taboot_http_port: int = 8000
    host: str = "0.0.0.0"

    @property
    def neo4j_connection_string(self) -> str:
        """Get Neo4j connection string with credentials."""
        return f"{self.neo4j_uri}?user={self.neo4j_user}&password={self.neo4j_password}&database={self.neo4j_db}"

    @property
    def postgres_connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@taboot-db:{self.postgres_port}/{self.postgres_db}"


# Singleton instance
_config: TabootConfig | None = None


def get_config() -> TabootConfig:
    """Get or create the singleton configuration instance.

    Returns:
        TabootConfig: The configuration instance loaded from environment variables.
    """
    global _config
    if _config is None:
        _config = TabootConfig()
    return _config


# Export convenience accessors
__all__ = ["TabootConfig", "get_config"]
