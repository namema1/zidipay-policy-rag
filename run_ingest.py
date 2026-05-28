"""CLI entry-point to (re)build the Chroma index from the corpus."""
from __future__ import annotations

import argparse
import sys
import time

from rag.config import CHROMA_DIR, CHUNK_OVERLAP, CHUNK_SIZE, CORPUS_DIR, set_seeds
from rag.ingest import build_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Zidipay RAG index.")
    parser.add_argument(
        "--corpus", default=str(CORPUS_DIR), help="Path to corpus directory."
    )
    parser.add_argument(
        "--persist", default=str(CHROMA_DIR), help="Path to Chroma persist directory."
    )
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP)
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Append to the existing index instead of rebuilding from scratch.",
    )
    args = parser.parse_args(argv)

    set_seeds()

    start = time.perf_counter()
    print(f"Building index from {args.corpus} -> {args.persist} ...")
    _, n_chunks = build_index(
        corpus_dir=args.corpus,
        persist_dir=args.persist,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        reset=not args.no_reset,
    )
    elapsed = time.perf_counter() - start
    print(f"Indexed {n_chunks} chunks in {elapsed:.1f}s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
