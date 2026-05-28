"""Shared fixtures: a tiny corpus + an in-memory index used across tests."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force the GROQ key to be a non-empty placeholder so importing modules that
# read it does not raise. Real Groq calls are stubbed in pipeline tests.
os.environ.setdefault("GROQ_API_KEY", "test-key-do-not-use")
os.environ.setdefault("USE_RERANKER", "false")


@pytest.fixture(scope="session")
def tiny_corpus(tmp_path_factory) -> Path:
    """A two-document fixture corpus with markdown headers."""
    base = tmp_path_factory.mktemp("tiny_corpus")
    (base / "leave.md").write_text(
        "# Leave Policy\n\n## Annual Leave\n"
        "Employees accrue 24 working days of annual leave per calendar year.\n\n"
        "## Sick Leave\n"
        "Employees are entitled to 14 days of paid sick leave per calendar year.\n",
        encoding="utf-8",
    )
    (base / "security.md").write_text(
        "# Security Policy\n\n## Passwords\n"
        "Use a 14-character passphrase for every account.\n\n"
        "## Incident Reporting\n"
        "Report any suspected incident within 60 minutes of discovery.\n",
        encoding="utf-8",
    )
    return base


@pytest.fixture()
def tiny_index(tiny_corpus, tmp_path):
    """Build a small Chroma index from the tiny corpus, isolated per test."""
    from rag.ingest import build_index

    persist = tmp_path / "chroma"
    persist.mkdir(parents=True, exist_ok=True)
    store, n = build_index(corpus_dir=tiny_corpus, persist_dir=persist, reset=True)
    yield store, n, persist
    shutil.rmtree(persist, ignore_errors=True)
