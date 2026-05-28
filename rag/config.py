"""Centralised configuration and reproducibility seeds."""
from __future__ import annotations

import os
import random
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
RERANKER_MODEL: str = os.getenv(
    "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
USE_RERANKER: bool = _bool(os.getenv("USE_RERANKER"), default=False)

TOP_K: int = _int(os.getenv("TOP_K"), 5)
K_FETCH: int = _int(os.getenv("K_FETCH"), 15)
CHUNK_SIZE: int = _int(os.getenv("CHUNK_SIZE"), 1100)
CHUNK_OVERLAP: int = _int(os.getenv("CHUNK_OVERLAP"), 150)
MAX_OUTPUT_TOKENS: int = _int(os.getenv("MAX_OUTPUT_TOKENS"), 512)
SCORE_THRESHOLD: float = _float(os.getenv("SCORE_THRESHOLD"), 0.30)
SEED: int = _int(os.getenv("SEED"), 42)
PORT: int = _int(os.getenv("PORT"), 5000)

CHROMA_DIR: Path = (PROJECT_ROOT / os.getenv("CHROMA_DIR", "data/chroma")).resolve()
CORPUS_DIR: Path = (PROJECT_ROOT / os.getenv("CORPUS_DIR", "corpus")).resolve()

REFUSAL_MESSAGE: str = (
    "I can only answer questions about Zidipay's policies and procedures."
)


def set_seeds(seed: int | None = None) -> None:
    """Pin every RNG we touch so retrieval/eval are reproducible."""
    s = seed if seed is not None else SEED
    os.environ["PYTHONHASHSEED"] = str(s)
    random.seed(s)
    try:
        import numpy as np

        np.random.seed(s)
    except ImportError:  # numpy is required, but stay safe
        pass


set_seeds()
