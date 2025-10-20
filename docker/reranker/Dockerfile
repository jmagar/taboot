FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODEL_ID=Qwen/Qwen3-Reranker-0.6B \
    BATCH_SIZE=16

WORKDIR /app

# Install system dependencies for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install fastapi uvicorn sentence-transformers==2.7.0

COPY app.py /app/app.py

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

