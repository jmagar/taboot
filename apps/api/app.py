"""Minimal FastAPI application stub for LlamaCrawl API."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="LlamaCrawl API",
    version="0.4.0",
    description="Doc-to-Graph RAG Platform",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "LlamaCrawl API v0.4.0", "docs": "/docs"}
