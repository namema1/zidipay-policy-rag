"""Build (or rebuild) the Chroma index from the corpus."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from rag.config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CORPUS_DIR,
    EMBEDDING_MODEL,
)
from rag.loaders import load_corpus


HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


def get_embeddings() -> HuggingFaceEmbeddings:
    """Local HF embeddings. No API key required; deterministic output."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _section_path(meta: dict) -> str:
    """Compose a 'H1 > H2 > H3' label from the splitter's header metadata."""
    parts = [meta.get("h1"), meta.get("h2"), meta.get("h3")]
    parts = [p.strip() for p in parts if p and isinstance(p, str)]
    return " > ".join(parts) if parts else ""


def chunk_documents(
    docs: Iterable[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    """Header-aware split for markdown; recursive split for HTML/PDF/TXT."""
    cs = chunk_size if chunk_size is not None else CHUNK_SIZE
    co = chunk_overlap if chunk_overlap is not None else CHUNK_OVERLAP

    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,
    )
    recursive = RecursiveCharacterTextSplitter(
        chunk_size=cs,
        chunk_overlap=co,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=True,
    )

    out: list[Document] = []
    chunk_counter: dict[str, int] = {}

    for doc in docs:
        fmt = doc.metadata.get("format", "")
        # Always start from the source content
        if fmt == "markdown":
            try:
                header_chunks = md_splitter.split_text(doc.page_content)
            except Exception:
                header_chunks = [doc]
            interim = header_chunks
        else:
            interim = [doc]

        # Apply recursive splitter to anything still oversized
        sub_chunks: list[Document] = []
        for piece in interim:
            piece_meta = {**doc.metadata, **getattr(piece, "metadata", {})}
            section = _section_path(piece_meta) or piece_meta.get("doc_title", "")
            content = piece.page_content if hasattr(piece, "page_content") else str(piece)
            if len(content) <= cs:
                sub_chunks.append(
                    Document(
                        page_content=content.strip(),
                        metadata={**piece_meta, "section": section},
                    )
                )
            else:
                for split in recursive.split_text(content):
                    sub_chunks.append(
                        Document(
                            page_content=split.strip(),
                            metadata={**piece_meta, "section": section},
                        )
                    )

        # Assign deterministic chunk_id
        for chunk in sub_chunks:
            if not chunk.page_content.strip():
                continue
            doc_id = chunk.metadata.get("doc_id", "doc")
            n = chunk_counter.get(doc_id, 0)
            chunk.metadata["chunk_id"] = f"{doc_id}:{n:04d}"
            chunk_counter[doc_id] = n + 1
            # Trim metadata to JSON-safe scalar types (Chroma requires non-None)
            chunk.metadata = {
                k: v
                for k, v in chunk.metadata.items()
                if isinstance(v, (str, int, float, bool))
            }
            out.append(chunk)

    return out


def build_index(
    corpus_dir: Path | str | None = None,
    persist_dir: Path | str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    reset: bool = True,
) -> tuple[Chroma, int]:
    """Load -> chunk -> embed -> persist. Returns (vectorstore, chunk_count)."""
    corpus = Path(corpus_dir) if corpus_dir is not None else CORPUS_DIR
    persist = Path(persist_dir) if persist_dir is not None else CHROMA_DIR
    persist.mkdir(parents=True, exist_ok=True)

    if reset and persist.exists():
        shutil.rmtree(persist)
        persist.mkdir(parents=True, exist_ok=True)

    docs = load_corpus(corpus)
    if not docs:
        raise RuntimeError(f"No documents found in {corpus}")

    chunks = chunk_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not chunks:
        raise RuntimeError("Chunking produced zero chunks — check the corpus.")

    embeddings = get_embeddings()
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(persist),
        collection_name="zidipay_policies",
    )
    return vectorstore, len(chunks)


def load_index(persist_dir: Path | None = None) -> Chroma:
    persist = persist_dir or CHROMA_DIR
    return Chroma(
        embedding_function=get_embeddings(),
        persist_directory=str(persist),
        collection_name="zidipay_policies",
    )


def index_chunk_count(persist_dir: Path | None = None) -> int:
    try:
        store = load_index(persist_dir)
        return store._collection.count()
    except Exception:
        return 0
