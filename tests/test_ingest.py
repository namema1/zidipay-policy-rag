"""Building the index from a tiny fixture corpus produces well-formed chunks."""
from __future__ import annotations


def test_build_tiny_index(tiny_index):
    store, n_chunks, persist = tiny_index
    assert n_chunks > 0
    # Pull every record and check required metadata exists
    collection = store._collection.get(include=["metadatas", "documents"])
    metadatas = collection["metadatas"]
    documents = collection["documents"]
    assert len(metadatas) == len(documents) == n_chunks
    for meta in metadatas:
        for key in ("doc_id", "doc_title", "source", "chunk_id"):
            assert key in meta, f"missing metadata key: {key}"
    # Both files should be represented
    doc_ids = {m["doc_id"] for m in metadatas}
    assert "leave" in doc_ids and "security" in doc_ids
