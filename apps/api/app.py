"""Minimal FastAPI application stub for Taboot API."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from apps.api.routes import init

app = FastAPI(
    title="Taboot API",
    version="0.4.0",
    description="Doc-to-Graph RAG Platform",
)

# Register routers
app.include_router(init.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Taboot API v0.4.0", "docs": "/docs"}
