"""Configuration management for Taboot platform.

Loads environment variables using pydantic-settings for type-safe configuration.
All service URLs, credentials, and tuning parameters are defined here.
"""

import os
from functools import lru_cache
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_LOADED = False
_ENV_LOCK = Lock()


def _is_running_in_container() -> bool:
    """Detect if code is running inside a Docker container.

    Checks for common container indicators:
    - /.dockerenv file (Docker)
    - DOCKER_CONTAINER environment variable
    - Container-specific cgroup entries

    Returns:
        bool: True if running in container, False if on host
    """
    # Check for /.dockerenv file
    if Path("/.dockerenv").exists():
        return True

    # Check for DOCKER_CONTAINER env var
    if os.getenv("DOCKER_CONTAINER"):
        return True

    # Check cgroup for docker/containerd
    try:
        with open("/proc/1/cgroup") as f:
            content = f.read()
            return "docker" in content or "containerd" in content
    except (FileNotFoundError, PermissionError):
        pass

    return False


def _resolve_env_file() -> str | None:
    """Locate the .env file regardless of the current working directory.

    Preference order:
        1. TABOOT_ENV_FILE environment variable (explicit override)
        2. Current working directory (common for local runs)
        3. Ancestors of this file (covers package execution within Docker)
    """
    override = os.getenv("TABOOT_ENV_FILE")
    if override:
        override_path = Path(override).expanduser()
        if override_path.is_file():
            return str(override_path)

    cwd_candidate = Path.cwd() / ".env"
    if cwd_candidate.is_file():
        return str(cwd_candidate)

    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return str(candidate)

    return None


_DEFAULT_ENV_FILE = _resolve_env_file()


def ensure_env_loaded() -> None:
    """Load environment variables from disk exactly once."""
    global _ENV_LOADED

    with _ENV_LOCK:
        if _ENV_LOADED:
            return

        env_path = _DEFAULT_ENV_FILE or _resolve_env_file()
        if env_path:
            load_dotenv(env_path, override=False)

        _ENV_LOADED = True


ensure_env_loaded()


class TeiConfig(BaseSettings):
    """Configuration block for Text Embeddings Inference service."""

    model_config = SettingsConfigDict(extra="ignore")

    url: HttpUrl
    batch_size: int = Field(default=32, ge=1, le=128)
    timeout: int = Field(default=30, ge=1, le=300)

    @field_validator("batch_size")
    @classmethod
    def _validate_batch_size(cls, value: int) -> int:
        if value % 8 != 0:
            raise ValueError("batch_size must be multiple of 8")
        return value


class TabootConfig(BaseSettings):
    """Main configuration class for Taboot platform.

    Loads all service URLs, credentials, and tuning parameters from environment variables.
    Uses pydantic-settings for validation and type safety.
    """

    model_config = SettingsConfigDict(
        env_file=_DEFAULT_ENV_FILE,
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
    neo4j_password: SecretStr = SecretStr("changeme")
    neo4j_db: str = "neo4j"

    postgres_user: str = "taboot"
    postgres_password: SecretStr = SecretStr("changeme")
    postgres_db: str = "taboot"
    postgres_host: str = "taboot-db"
    postgres_port: int = 5432

    # ========== Connection Pooling ==========
    neo4j_max_pool_size: int = 50
    neo4j_connection_timeout: int = 30
    redis_max_connections: int = 100
    redis_socket_timeout: int = 10
    qdrant_max_connections: int = 200
    postgres_min_pool_size: int = 5
    postgres_max_pool_size: int = 20

    # ========== Vector & Embedding Config ==========
    collection_name: str = "documents"
    tei_embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    qdrant_embedding_dim: int = 1024
    tei_timeout: int = Field(default=30, ge=1, le=300)
    tei_max_concurrent_requests: int = 80
    tei_max_batch_tokens: int = 163840
    tei_tokenization_workers: int = 8

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
    embedding_batch_size: int = Field(default=64, ge=1, le=128)
    qdrant_upsert_batch_size: int = 200  # Qdrant upsert batch size
    ingest_flush_threshold: int = 1000  # Flush threshold for ingestion
    enable_ingest_events: bool = False
    ingest_events_stream: str = "stream:documents"
    ingest_events_group: str = "ingestion-events"
    ingest_events_consumer_prefix: str = "worker"

    # ========== External API Credentials (Optional) ==========
    github_token: SecretStr | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: SecretStr | None = None
    reddit_user_agent: str = "Script"
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_oauth_refresh_token: SecretStr | None = None
    elasticsearch_url: str | None = None
    elasticsearch_api_key: SecretStr | None = None
    tailscale_api_key: str | None = None
    unifi_username: str | None = None
    unifi_password: SecretStr | None = None
    unifi_api_token: SecretStr | None = None

    # ========== Firecrawl Config ==========
    firecrawl_api_key: SecretStr = SecretStr("changeme")
    num_workers_per_queue: int = 16
    worker_concurrency: int = 8
    scrape_concurrency: int = 8
    retry_delay: int = 1000
    max_retries: int = 1

    # ========== Neo4j Memory Config ==========
    neo4j_heap_initial_size: str = "2G"
    neo4j_heap_max_size: str = "2G"
    neo4j_pagecache_size: str = "2G"

    # ========== Observability ==========
    log_level: str = "INFO"
    health_check_timeout: float = 5.0

    # ========== API Service ==========
    taboot_http_port: int = 8000
    host: str = "0.0.0.0"
    cors_allow_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3003",
    ]  # Override via CORS_ALLOW_ORIGINS env var (comma-separated)

    def model_post_init(self, __context: object) -> None:
        """Post-initialization hook to rewrite URLs for host execution.

        When running on host (not in container), rewrites container hostnames
        to localhost with mapped ports from docker-compose.yaml.
        """
        super().model_post_init(__context)

        if not _is_running_in_container():
            # Rewrite URLs to use localhost with mapped ports
            self.tei_embedding_url = "http://localhost:8080"
            self.qdrant_url = "http://localhost:7000"
            self.neo4j_uri = "bolt://localhost:7687"
            self.redis_url = "redis://localhost:6379"
            self.reranker_url = "http://localhost:8081"
            self.firecrawl_api_url = "http://localhost:3002"
            self.playwright_microservice_url = "http://localhost:3000/scrape"

    @field_validator("embedding_batch_size")
    @classmethod
    def _validate_embedding_batch_size(cls, value: int) -> int:
        if value % 8 != 0:
            raise ValueError("embedding_batch_size must be a multiple of 8")
        return value

    @property
    def tei_config(self) -> TeiConfig:
        """Return validated TEI configuration block."""

        return TeiConfig(
            url=self.tei_embedding_url,
            batch_size=self.embedding_batch_size,
            timeout=self.tei_timeout,
        )

    @property
    def neo4j_connection_string(self) -> str:
        """Get Neo4j connection string with credentials."""
        pwd = self.neo4j_password.get_secret_value()
        return f"{self.neo4j_uri}?user={self.neo4j_user}&password={pwd}&database={self.neo4j_db}"

    @property
    def postgres_connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        pwd = self.postgres_password.get_secret_value()
        return f"postgresql://{self.postgres_user}:{pwd}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


@lru_cache(maxsize=1)
def get_config() -> TabootConfig:
    """Return cached Settings instance (thread-safe, process-local).

    Uses lru_cache to ensure a single instance is created and reused.
    Thread-safe through Python's GIL for cache access.

    Returns:
        TabootConfig: The configuration instance loaded from environment variables.
    """
    return TabootConfig()


# Export convenience accessors
__all__ = ["TabootConfig", "TeiConfig", "ensure_env_loaded", "get_config"]
