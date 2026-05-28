"""Retrieving against the tiny index returns at least one chunk with full metadata."""
from __future__ import annotations


def test_retrieval_returns_chunks(monkeypatch, tiny_index):
    store, _n, persist = tiny_index

    # Point load_index() at the tiny store
    from rag import retriever, ingest

    monkeypatch.setattr(ingest, "load_index", lambda *_a, **_k: store)

    results = retriever.retrieve("How many days of annual leave?", top_k=3, k_fetch=5)
    assert results, "retriever returned no results"
    top_doc, top_score = results[0]
    assert top_doc.page_content
    for key in ("doc_id", "doc_title", "source"):
        assert key in top_doc.metadata, f"missing {key} on retrieved chunk"
    # Score should be a finite float
    assert isinstance(top_score, float)
