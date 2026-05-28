"""The Flask app and core modules must import cleanly."""
from __future__ import annotations


def test_import_app():
    import app  # noqa: F401


def test_import_pipeline():
    from rag import pipeline  # noqa: F401
    from rag import generate  # noqa: F401
    from rag import retriever  # noqa: F401
    from rag import ingest  # noqa: F401
    from rag import loaders  # noqa: F401
    from rag import config  # noqa: F401
