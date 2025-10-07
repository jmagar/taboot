"""Live end-to-end checks for the LlamaCrawl pipeline.

These tests execute the real CLI against the running stack (Firecrawl, TEI,
Qdrant, Redis, Neo4j). They are skipped unless the environment variable
``LLAMACRAWL_LIVE_TESTS`` is set to ``"1"`` so routine CI runs are unaffected.

You can optionally override the Firecrawl crawl URL via
``LLAMACRAWL_TEST_URL`` and the ingestion limit via
``LLAMACRAWL_TEST_LIMIT`` to keep runs deterministic.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

import pytest


LIVE_TESTS_ENABLED = os.getenv("LLAMACRAWL_LIVE_TESTS") == "1"
DEFAULT_TEST_URL = "https://docs.anthropic.com/en/api/agent-sdk/overview"
SUMMARY_PATTERN = re.compile(
    r"Ingestion Summary:\s*\n(?P<body>(?:\s{2}.+\n)+)", re.MULTILINE
)


def _run_cli(command: list[str]) -> tuple[int, str, str, float]:
    start = time.perf_counter()
    proc = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    duration = time.perf_counter() - start
    return proc.returncode, proc.stdout, proc.stderr, duration


def _extract_summary(raw: str) -> dict[str, float]:
    match = SUMMARY_PATTERN.search(raw)
    if not match:
        return {}
    summary: dict[str, float] = {}
    for line in match.group("body").strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.strip().split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if value.endswith("s") and "duration" in key:
            value = value[:-1]
        try:
            summary[key] = float(value)
        except ValueError:
            continue
    return summary


@pytest.mark.skipif(
    not LIVE_TESTS_ENABLED,
    reason="set LLAMACRAWL_LIVE_TESTS=1 to run live Firecrawl/ingestion checks",
)
def test_live_firecrawl_crawl(tmp_path: Path) -> None:
    test_url = os.getenv("LLAMACRAWL_TEST_URL", DEFAULT_TEST_URL)
    limit = os.getenv("LLAMACRAWL_TEST_LIMIT", "15")
    command = [
        "uv",
        "run",
        "llamacrawl",
        "crawl",
        test_url,
        "--limit",
        limit,
        "--max-depth",
        "1",
        "--log-level",
        "INFO",
    ]

    returncode, stdout, stderr, duration = _run_cli(command)
    metrics = {
        "command": " ".join(command),
        "duration_seconds": duration,
        "returncode": returncode,
    }
    (tmp_path / "firecrawl_crawl_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    assert returncode == 0, stderr
    assert "Successfully ingested" in stdout or "No documents" in stdout


@pytest.mark.skipif(
    not LIVE_TESTS_ENABLED,
    reason="set LLAMACRAWL_LIVE_TESTS=1 to run live Firecrawl/ingestion checks",
)
def test_live_firecrawl_ingest(tmp_path: Path) -> None:
    limit = os.getenv("LLAMACRAWL_TEST_LIMIT", "50")
    command = [
        "uv",
        "run",
        "llamacrawl",
        "ingest",
        "firecrawl",
        "--limit",
        limit,
    ]

    returncode, stdout, stderr, duration = _run_cli(command)
    summary = _extract_summary(stdout)

    metrics = {
        "command": " ".join(command),
        "duration_seconds": duration,
        "returncode": returncode,
        "summary": summary,
    }
    (tmp_path / "firecrawl_ingest_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    assert returncode == 0, stderr
    assert summary, "Ingestion summary not found in CLI output"
    assert summary.get("total_documents_loaded", 0) > 0
    # Ensure throughput is reasonable (guard rail; adjust if hardware differs)
    docs_per_second = summary["total_documents_loaded"] / max(summary["duration"], 1.0)
    assert docs_per_second > 0.5, f"Throughput too low: {docs_per_second:.2f} docs/s"
