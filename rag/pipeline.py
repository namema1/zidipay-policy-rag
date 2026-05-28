"""End-to-end RAG pipeline: retrieve → generate → measure."""
from __future__ import annotations

import time
from dataclasses import asdict
from typing import Optional

from rag.generate import generate_answer
from rag.retriever import retrieve


def answer(
    question: str,
    top_k: Optional[int] = None,
    k_fetch: Optional[int] = None,
    use_reranker: Optional[bool] = None,
    score_threshold: Optional[float] = None,
    llm=None,
) -> dict:
    """Run the full pipeline and return a JSON-serialisable result.

    Keys:
      - answer (str)
      - citations (list[dict])  # serialised Citation objects
      - contexts (list[dict])   # the retrieved chunks (with metadata + score)
      - latency_ms (int)
      - refused (bool)
    """
    if not question or not question.strip():
        return {
            "answer": "Please ask a question about Zidipay's policies.",
            "citations": [],
            "contexts": [],
            "latency_ms": 0,
            "refused": True,
        }

    start = time.perf_counter()
    results = retrieve(
        question,
        top_k=top_k,
        k_fetch=k_fetch,
        use_reranker=use_reranker,
    )
    gen = generate_answer(
        question,
        results,
        score_threshold=score_threshold,
        llm=llm,
    )
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    contexts = [
        {
            "doc_id": doc.metadata.get("doc_id", ""),
            "doc_title": doc.metadata.get("doc_title", ""),
            "section": doc.metadata.get("section", ""),
            "source": doc.metadata.get("source", ""),
            "chunk_id": doc.metadata.get("chunk_id", ""),
            "score": float(score),
            "snippet": doc.page_content[:500],
        }
        for doc, score in results
    ]

    return {
        "answer": gen["answer"],
        "citations": [asdict(c) for c in gen["citations"]],
        "contexts": contexts,
        "latency_ms": elapsed_ms,
        "refused": gen["refused"],
    }
