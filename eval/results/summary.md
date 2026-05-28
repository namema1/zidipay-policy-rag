# Zidipay Policy RAG — Evaluation Summary

- In-corpus questions: **20**
- Out-of-corpus questions: **4**

## Information-quality metrics

| Metric | Value |
| --- | --- |
| Groundedness (fully supported, LLM judge) | **85.0%** |
| Groundedness (with partial = 0.5) | 85.0% |
| Citation accuracy (LLM judge) | **85.0%** |
| Citation accuracy (deterministic, expected doc cited) | 95.0% |
| Citation accuracy (deterministic, expected section keyword in citation) | 65.0% |
| Refusal correctness (in-corpus, not refused) | 95.0% |
| Refusal correctness (out-of-corpus, refused) | **100.0%** |
| Refusal overall | 95.8% |
| Substring match vs gold answer | 0.0% |
| Partial match (substring or ≥0.5 token overlap) | 85.0% |

## System metrics

| Metric | Value |
| --- | --- |
| Latency p50 | **4440 ms** |
| Latency p95 | **5867 ms** |

Config: `{"top_k": null, "chunk_size": null, "use_reranker": null}`.
