"""Generate OpenAPI specification for the FastAPI app."""

from __future__ import annotations

import json
from pathlib import Path

from apps.api.app import app


def main(output: str = "openapi.json") -> None:
    """Write the OpenAPI schema to the given output path."""

    schema = app.openapi()
    output_path = Path(output)
    output_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"Generated OpenAPI schema at {output_path}")


if __name__ == "__main__":
    main()
