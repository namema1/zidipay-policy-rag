"""Pipeline behaviour: in-corpus → citations; out-of-corpus → refusal.

The Groq call is stubbed so this test runs offline (no GROQ_API_KEY required).
"""
from __future__ import annotations


class _FakeAIMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChat:
    """Stand-in for ChatGroq that echoes a deterministic templated answer."""

    def __init__(self, response_text: str):
        self._response_text = response_text

    def invoke(self, _messages):
        return _FakeAIMessage(self._response_text)


def test_in_corpus_returns_citations(monkeypatch, tiny_index):
    store, _n, _persist = tiny_index
    from rag import ingest, generate, pipeline

    monkeypatch.setattr(ingest, "load_index", lambda *_a, **_k: store)

    fake = _FakeChat("Employees get 24 days of annual leave per year [1].")
    monkeypatch.setattr(generate, "_make_llm", lambda *_a, **_k: fake)

    result = pipeline.answer("How many days of annual leave do I get?")
    assert result["refused"] is False
    assert "24" in result["answer"]
    assert result["citations"], "expected at least one citation"
    cite = result["citations"][0]
    for key in ("doc_id", "doc_title", "section", "source", "snippet"):
        assert key in cite, f"missing citation field: {key}"
    assert result["latency_ms"] >= 0


def test_out_of_corpus_refuses(monkeypatch, tiny_index):
    store, _n, _persist = tiny_index
    from rag import ingest, generate, pipeline

    monkeypatch.setattr(ingest, "load_index", lambda *_a, **_k: store)

    # The LLM would refuse, but with the score gate this should never reach the model.
    fake = _FakeChat("I can only answer questions about Zidipay's policies and procedures.")
    monkeypatch.setattr(generate, "_make_llm", lambda *_a, **_k: fake)

    # Force the refusal gate to trip by setting a very high score threshold
    result = pipeline.answer("Who won the 2026 UEFA Champions League?", score_threshold=0.99)
    assert result["refused"] is True
    assert "Zidipay" in result["answer"]
    assert result["citations"] == []
