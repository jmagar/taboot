from unittest.mock import MagicMock

import pytest

from llamacrawl.config import GitHubSourceConfig
from llamacrawl.readers.github import GitHubReader
from llamacrawl.storage.redis import RedisClient


def test_github_source_config_accepts_owner_entries() -> None:
    config = GitHubSourceConfig(repositories=["octocat"])
    assert config.repositories == ["octocat"]


def test_github_reader_expands_owner_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    redis_client = MagicMock(spec=RedisClient)

    def fake_fetch(self: GitHubReader, owner: str) -> list[str]:
        if owner == "octocat":
            return ["octocat/hello-world", "octocat/spoon-knife"]
        if owner == "jmagar":
            return ["jmagar/docker-mcp", "octocat/hello-world"]
        return []

    monkeypatch.setattr(
        GitHubReader,
        "_fetch_owner_repositories",
        fake_fetch,
        raising=True,
    )

    reader = GitHubReader(
        "github",
        {
            "repositories": [
                "octocat",
                "jmagar/docker-mcp",
                "jmagar",
            ],
            "include_issues": False,
            "include_prs": False,
        },
        redis_client,
    )

    assert reader.owner_targets == ["octocat", "jmagar"]
    assert reader.repositories == [
        "jmagar/docker-mcp",
        "octocat/hello-world",
        "octocat/spoon-knife",
    ]
