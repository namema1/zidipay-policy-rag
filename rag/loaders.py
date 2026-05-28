"""Load every document type in the corpus and attach uniform metadata."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    BSHTMLLoader,
    PyPDFLoader,
    TextLoader,
)

from rag.config import CORPUS_DIR


SUPPORTED_EXTS = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf"}


def _slug_to_id(stem: str) -> str:
    """Stable doc_id derived from filename stem."""
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")


def _extract_h1(text: str) -> str:
    """Pick a reasonable title from markdown/HTML/PDF text."""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # markdown H1
        if line.startswith("#"):
            return line.lstrip("# ").strip()
        # first non-empty line if it looks title-ish
        if len(line) < 200:
            return line
    return "Untitled"


_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def _clean(text: str) -> str:
    if not text:
        return ""
    # normalise newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def _load_markdown(path: Path) -> list[Document]:
    text = _clean(path.read_text(encoding="utf-8"))
    title = _extract_h1(text)
    return [
        Document(
            page_content=text,
            metadata={
                "source": path.name,
                "doc_title": title,
                "doc_id": _slug_to_id(path.stem),
                "format": "markdown",
            },
        )
    ]


def _load_text(path: Path) -> list[Document]:
    text = _clean(path.read_text(encoding="utf-8"))
    title = _extract_h1(text)
    return [
        Document(
            page_content=text,
            metadata={
                "source": path.name,
                "doc_title": title,
                "doc_id": _slug_to_id(path.stem),
                "format": "text",
            },
        )
    ]


def _load_html(path: Path) -> list[Document]:
    loader = BSHTMLLoader(str(path), open_encoding="utf-8")
    docs = loader.load()
    out: list[Document] = []
    for d in docs:
        cleaned = _clean(d.page_content)
        if not cleaned:
            continue
        # BSHTMLLoader puts the <title> in metadata["title"]
        title = (d.metadata.get("title") or _extract_h1(cleaned)).strip()
        out.append(
            Document(
                page_content=cleaned,
                metadata={
                    "source": path.name,
                    "doc_title": title,
                    "doc_id": _slug_to_id(path.stem),
                    "format": "html",
                },
            )
        )
    return out


def _load_pdf(path: Path) -> list[Document]:
    loader = PyPDFLoader(str(path))
    pages = loader.load()
    # Concatenate pages — we want section-level chunks across pages, not page chunks.
    full = _clean("\n\n".join(p.page_content for p in pages))
    title = _extract_h1(full)
    return [
        Document(
            page_content=full,
            metadata={
                "source": path.name,
                "doc_title": title,
                "doc_id": _slug_to_id(path.stem),
                "format": "pdf",
                "page_count": len(pages),
            },
        )
    ]


_LOADERS = {
    ".md": _load_markdown,
    ".markdown": _load_markdown,
    ".txt": _load_text,
    ".html": _load_html,
    ".htm": _load_html,
    ".pdf": _load_pdf,
}


def load_one(path: Path) -> list[Document]:
    ext = path.suffix.lower()
    if ext not in _LOADERS:
        raise ValueError(f"Unsupported extension {ext} for {path}")
    return _LOADERS[ext](path)


def load_corpus(corpus_dir: Path | None = None) -> list[Document]:
    """Load every supported file in `corpus_dir` and return a flat list of Documents."""
    base = (corpus_dir or CORPUS_DIR).resolve()
    if not base.exists():
        raise FileNotFoundError(f"Corpus directory does not exist: {base}")
    docs: list[Document] = []
    for path in sorted(base.iterdir()):
        if path.is_dir() or path.suffix.lower() not in SUPPORTED_EXTS:
            continue
        docs.extend(load_one(path))
    return docs


def iter_corpus_files(corpus_dir: Path | None = None) -> Iterable[Path]:
    base = (corpus_dir or CORPUS_DIR).resolve()
    for path in sorted(base.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            yield path
