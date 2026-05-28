"""Flask /health endpoint returns the expected JSON."""
from __future__ import annotations

import json


def test_health_endpoint(monkeypatch):
    # Don't build the real index when importing the app for this test.
    monkeypatch.setenv("CHROMA_DIR", "data/chroma")
    import app as flask_app

    # Stub index_chunk_count to avoid touching disk during the test
    monkeypatch.setattr(flask_app, "index_chunk_count", lambda *_a, **_k: 42)

    client = flask_app.app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload["status"] == "ok"
    assert payload["index_chunks"] == 42
    assert "model" in payload
