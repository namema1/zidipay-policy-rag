FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

WORKDIR /app

# System packages needed by lxml / unstructured / pypdf
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
        libjpeg-dev \
        zlib1g-dev \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Pre-download the embedding model so cold starts on the Space are fast.
RUN python -c "from langchain_huggingface import HuggingFaceEmbeddings; \
    HuggingFaceEmbeddings(model_name='BAAI/bge-small-en-v1.5')"
# Pre-download the cross-encoder (used when USE_RERANKER=true). Optional.
RUN python -c "from sentence_transformers import CrossEncoder; \
    CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')" || true

COPY . /app

# Make the cache and persist dirs writable by the runtime user
RUN mkdir -p /app/data/chroma /app/.cache && chmod -R 777 /app/data /app/.cache

# Pre-build the Chroma index at image build time. HF Spaces mounts /app
# read-only at runtime, so we cannot build on first request.
RUN python -c "from rag.ingest import build_index; _, n = build_index(); print(f'Built index with {n} chunks.')"

EXPOSE 7860
ENV PORT=7860 \
    CHROMA_DIR=/tmp/chroma

# At runtime, copy the baked index to /tmp (the only reliably writable path on
# HF Spaces) so Chroma's SQLite can open it read-write for queries.
CMD ["sh", "-c", "rm -rf /tmp/chroma && cp -r /app/data/chroma /tmp/chroma && gunicorn -b 0.0.0.0:${PORT:-7860} --workers 1 --threads 4 --timeout 180 app:app"]
