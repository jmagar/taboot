"""Tests for Tier A deterministic parsers (code blocks, tables, YAML/JSON)."""

from packages.extraction.tier_a.parsers import (
    parse_code_blocks,
    parse_tables,
    parse_yaml_json,
)


class TestCodeBlockParser:
    """Test fenced code block extraction."""

    def test_parse_single_code_block(self) -> None:
        """Test parsing a single fenced code block."""
        content = """
Some text before.

```python
def hello() -> None:
    print("Hello, world!")
```

Some text after.
"""
        blocks = parse_code_blocks(content)

        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"
        assert "def hello()" in blocks[0]["code"]
        assert 'print("Hello, world!")' in blocks[0]["code"]

    def test_parse_multiple_code_blocks(self) -> None:
        """Test parsing multiple fenced code blocks."""
        content = """
```yaml
version: '3'
services:
  app:
    image: myapp:latest
```

Some text.

```bash
docker-compose up -d
```
"""
        blocks = parse_code_blocks(content)

        assert len(blocks) == 2
        assert blocks[0]["language"] == "yaml"
        assert blocks[1]["language"] == "bash"
        assert "docker-compose up -d" in blocks[1]["code"]

    def test_parse_code_block_no_language(self) -> None:
        """Test parsing code block without language specified."""
        content = """
```
generic code block
```
"""
        blocks = parse_code_blocks(content)

        assert len(blocks) == 1
        assert blocks[0]["language"] == ""
        assert "generic code block" in blocks[0]["code"]

    def test_parse_empty_content(self) -> None:
        """Test parsing empty content returns empty list."""
        blocks = parse_code_blocks("")
        assert blocks == []

    def test_parse_content_without_code_blocks(self) -> None:
        """Test content without code blocks returns empty list."""
        content = "Just plain text with no code blocks."
        blocks = parse_code_blocks(content)
        assert blocks == []


class TestTableParser:
    """Test markdown table extraction."""

    def test_parse_simple_table(self) -> None:
        """Test parsing a simple markdown table."""
        content = """
| Service | Port | Protocol |
|---------|------|----------|
| api     | 8080 | HTTP     |
| db      | 5432 | TCP      |
"""
        tables = parse_tables(content)

        assert len(tables) == 1
        table = tables[0]
        assert table["headers"] == ["Service", "Port", "Protocol"]
        assert len(table["rows"]) == 2
        assert table["rows"][0] == ["api", "8080", "HTTP"]
        assert table["rows"][1] == ["db", "5432", "TCP"]

    def test_parse_empty_content(self) -> None:
        """Test parsing empty content returns empty list."""
        tables = parse_tables("")
        assert tables == []

    def test_parse_content_without_tables(self) -> None:
        """Test content without tables returns empty list."""
        content = "Just plain text with no tables."
        tables = parse_tables(content)
        assert tables == []


class TestYAMLJSONParser:
    """Test YAML/JSON structure extraction."""

    def test_parse_yaml_docker_compose(self) -> None:
        """Test parsing YAML (Docker Compose)."""
        yaml_content = """
version: '3.8'
services:
  api:
    image: myapp/api:v1.0.0
    ports:
      - "8080:8080"
    depends_on:
      - db
  db:
    image: postgres:15
    ports:
      - "5432:5432"
"""
        result = parse_yaml_json(yaml_content, format_type="yaml")

        assert result is not None
        assert isinstance(result, dict)
        assert "services" in result
        assert "api" in result["services"]
        assert "db" in result["services"]
        assert result["services"]["api"]["image"] == "myapp/api:v1.0.0"
        assert result["services"]["api"]["depends_on"] == ["db"]

    def test_parse_json_object(self) -> None:
        """Test parsing JSON object."""
        json_content = """
{
  "service": "api",
  "port": 8080,
  "dependencies": ["db", "cache"]
}
"""
        result = parse_yaml_json(json_content, format_type="json")

        assert result is not None
        assert isinstance(result, dict)
        assert result["service"] == "api"
        assert result["port"] == 8080
        assert result["dependencies"] == ["db", "cache"]

    def test_parse_invalid_yaml_returns_none(self) -> None:
        """Test parsing invalid YAML returns None."""
        invalid_yaml = """
invalid: yaml: syntax:
  - broken
    indentation
"""
        result = parse_yaml_json(invalid_yaml, format_type="yaml")
        assert result is None

    def test_parse_invalid_json_returns_none(self) -> None:
        """Test parsing invalid JSON returns None."""
        invalid_json = '{"broken": "json" invalid}'
        result = parse_yaml_json(invalid_json, format_type="json")
        assert result is None

    def test_parse_empty_content_returns_none(self) -> None:
        """Test parsing empty content returns None."""
        result = parse_yaml_json("", format_type="yaml")
        assert result is None
