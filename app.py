"""Flask front-end for the Zidipay Policy RAG."""
from __future__ import annotations

import json
import os
from pathlib import Path

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

from rag.config import CHROMA_DIR, CORPUS_DIR, GROQ_MODEL, PORT
from rag.ingest import build_index, index_chunk_count
from rag.pipeline import answer as rag_answer

app = Flask(__name__, template_folder="templates", static_folder="static")


def _ensure_index() -> None:
    """If the persist dir is empty/missing, build the index on startup."""
    count = index_chunk_count(CHROMA_DIR)
    if count > 0:
        app.logger.info("Found existing Chroma index with %d chunks.", count)
        return
    app.logger.warning("No Chroma index found at %s — building from corpus.", CHROMA_DIR)
    _, n = build_index(corpus_dir=CORPUS_DIR, persist_dir=CHROMA_DIR, reset=True)
    app.logger.info("Built index with %d chunks.", n)


@app.route("/")
def index() -> str:
    return render_template("index.html", model=GROQ_MODEL)


@app.route("/health", methods=["GET"])
def health() -> Response:
    chunks = index_chunk_count(CHROMA_DIR)
    payload = {
        "status": "ok",
        "model": GROQ_MODEL,
        "index_chunks": int(chunks),
    }
    return Response(json.dumps(payload), mimetype="application/json")


@app.route("/chat", methods=["POST"])
def chat() -> Response:
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify(
            {
                "answer": "Please enter a question about Zidipay's policies.",
                "citations": [],
                "latency_ms": 0,
                "refused": True,
            }
        ), 400

    result = rag_answer(question)
    # Front-end doesn't need the raw context dump
    return jsonify(
        {
            "answer": result["answer"],
            "citations": result["citations"],
            "latency_ms": result["latency_ms"],
            "refused": result["refused"],
        }
    )


def _resolve_source_path(doc_id: str) -> Path | None:
    """Find the corpus file whose stem slugifies to `doc_id`."""
    import re

    def _slug(stem: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")

    for path in CORPUS_DIR.iterdir():
        if path.is_file() and _slug(path.stem) == doc_id:
            return path
    return None


@app.route("/source/<doc_id>", methods=["GET"])
def source(doc_id: str) -> Response:
    path = _resolve_source_path(doc_id)
    if path is None:
        abort(404)
    # Serve from the corpus directory; choose mimetype by extension
    mime = {
        ".md": "text/markdown; charset=utf-8",
        ".markdown": "text/markdown; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".htm": "text/html; charset=utf-8",
        ".pdf": "application/pdf",
    }.get(path.suffix.lower(), "application/octet-stream")
    return send_from_directory(
        str(path.parent),
        path.name,
        mimetype=mime,
        as_attachment=False,
    )


with app.app_context():
    try:
        _ensure_index()
    except Exception as exc:
        app.logger.error("Index bootstrap failed: %s", exc)


if __name__ == "__main__":
    port = int(os.getenv("PORT", PORT))
    app.run(host="0.0.0.0", port=port, debug=False)
