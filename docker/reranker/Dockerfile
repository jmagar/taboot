# syntax=docker/dockerfile:1.7-labs

FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

# Enable fail-fast
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODEL_ID=Qwen/Qwen3-Reranker-0.6B \
    BATCH_SIZE=16

WORKDIR /app

# Install system dependencies for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Pin pip version for reproducibility
RUN pip install --no-cache-dir pip==24.3.1

# Install pinned dependencies with BuildKit cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
      fastapi==0.119.0 \
      uvicorn==0.37.0 \
      sentence-transformers==2.7.0

# Pre-download model BEFORE copying application code (better caching)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Qwen/Qwen3-Reranker-0.6B')"

# Copy application code LAST (changes most frequently)
COPY app.py /app/app.py

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
