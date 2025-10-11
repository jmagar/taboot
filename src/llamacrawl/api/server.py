"""Entry point for launching the LlamaCrawl FastAPI server."""

from __future__ import annotations

import uvicorn


def main() -> None:
    """Run the FastAPI application using uvicorn."""
    uvicorn.run(
        "llamacrawl.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
