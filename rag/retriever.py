"""Retrieve relevant chunks for a query, with optional cross-encoder reranking."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from langchain_core.documents import Document

from rag import ingest as _ingest
from rag.config import K_FETCH, RERANKER_MODEL, TOP_K, USE_RERANKER


@lru_cache(maxsize=1)
def _get_reranker():
    """Lazily load a sentence-transformers cross-encoder (only when enabled)."""
    from sentence_transformers import CrossEncoder

    return CrossEncoder(RERANKER_MODEL)


def _similarity_from_distance(distance: float) -> float:
    """Chroma returns L2 / cosine *distance*; map it to a [0,1] similarity-ish score.

    For cosine distance (Chroma default with normalized vectors) the value is in [0, 2],
    where 0 = identical. similarity = 1 - distance/2 lands in [0, 1].
    """
    if distance is None:
        return 0.0
    sim = 1.0 - (float(distance) / 2.0)
    if sim < 0.0:
        sim = 0.0
    if sim > 1.0:
        sim = 1.0
    return sim


def retrieve(
    query: str,
    top_k: Optional[int] = None,
    k_fetch: Optional[int] = None,
    use_reranker: Optional[bool] = None,
) -> list[tuple[Document, float]]:
    """Similarity-search then (optionally) cross-encoder rerank.

    Returns a list of (Document, similarity_score) pairs ordered best-first.
    """
    k = top_k if top_k is not None else TOP_K
    fetch = k_fetch if k_fetch is not None else K_FETCH
    rerank = use_reranker if use_reranker is not None else USE_RERANKER

    store = _ingest.load_index()
    raw = store.similarity_search_with_score(query, k=fetch)
    if not raw:
        return []

    candidates = [(doc, _similarity_from_distance(score)) for doc, score in raw]

    if not rerank:
        return candidates[:k]

    # cross-encoder rerank over the candidates
    cross = _get_reranker()
    pairs = [(query, doc.page_content) for doc, _ in candidates]
    rerank_scores = cross.predict(pairs)
    rescored = sorted(
        zip([d for d, _ in candidates], rerank_scores),
        key=lambda x: float(x[1]),
        reverse=True,
    )
    # Map rerank scores into 0..1 with a sigmoid so the refusal gate stays comparable
    import math

    def _sig(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-float(x)))

    return [(doc, _sig(s)) for doc, s in rescored[:k]]


def best_score(results: list[tuple[Document, float]]) -> float:
    return results[0][1] if results else 0.0
