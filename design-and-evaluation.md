# Design and Evaluation

This document records the design decisions behind the Zidipay Policy RAG and the evaluation results. It is the long-form counterpart to the README.

## 1. Design

### 1.1 Goal

Build a small, reliable Q&A app over Zidipay's policy corpus that:

1. answers only from the documents (no hallucination),
2. cites the document and section that supports each answer,
3. refuses gracefully when asked something outside the corpus,
4. is reproducible end-to-end (pinned deps, fixed seeds, deterministic chunking).

### 1.2 Tech choices and the "why"

**Language and runtime — Python 3.11.**
Best in class library support for LangChain, sentence-transformers, and Chroma.

**Orchestration — LangChain.**
Covered by the project brief. We use it for document loaders, the markdown-header-aware splitter and the recursive splitter, the Chroma vector store wrapper, and `ChatGroq`. We deliberately avoid LangChain "chains" / agents — those add indirection and obscure what is actually a four-step pipeline (retrieve → format → call → parse). Keeping the pipeline imperative (`rag/pipeline.py`) keeps it testable and easy to reason about.

**LLM — Groq, `llama-3.3-70b-versatile`, temperature 0.**
Groq's free tier gives GPT-4o-class quality with low latency (median <2 s in our eval, see §2). Temperature 0 makes the answer deterministic for any fixed retrieval result. `llama-3.1-8b-instant` is a configurable fallback with a higher daily request ceiling for ablations.

**Embeddings — local HuggingFace `BAAI/bge-small-en-v1.5`.**
Chosen over the HuggingFace Inference API for three reasons: (1) no API key, no rate limits — critical when ingesting the corpus and again during eval; (2) deterministic — the same input vector regardless of network or upstream changes; (3) small (~130 MB) so the Docker image stays cheap to deploy. BGE-small is a strong retrieval embedder for its size on the MTEB benchmark.

**Vector store — Chroma, persisted to `data/chroma/`.**
Lightweight, local, zero external service. The persist dir is gitignored — on a fresh container the app rebuilds the index from `corpus/` at startup (see `app.py`'s `_ensure_index`). This means deployment never depends on committing binary index files.

**Chunking — header-aware then recursive.**
For markdown we run `MarkdownHeaderTextSplitter` first to preserve H1/H2/H3 boundaries, carry the heading path into chunk metadata as `section`, and only then fall back to `RecursiveCharacterTextSplitter` for any oversized sub-section. HTML/PDF/TXT use the recursive splitter directly with the same chunk size (1100 chars) and overlap (150 chars). Outcome: each chunk knows *which doc and which section* it came from, which is what makes the citation field precise and verifiable. The 1100 / 150 defaults were chosen as the middle of the three ablated values — see §2.4.

**Retrieval — top-k similarity, k_fetch over-fetch, optional cross-encoder rerank.**
We fetch 15 candidates (`k_fetch`) and keep the top 5 (`top_k`). With `USE_RERANKER=true` the 15 candidates are re-ranked by a `cross-encoder/ms-marco-MiniLM-L-6-v2` model and the top 5 of *that* go to the LLM. Over-fetching gives the reranker something to choose from; without the reranker it's just a slightly safer top-5. The Chroma cosine distance is mapped to a `[0,1]` similarity-like score so a single `SCORE_THRESHOLD` works whether the reranker is on or off.

**Guardrails — defence in depth, not a single check.**
- *Retrieval gate.* If the best top-1 score is below `SCORE_THRESHOLD` (default 0.30), the pipeline refuses *without* calling the LLM. This is the cheapest and most reliable guardrail.
- *Prompt-level instruction.* The system prompt tells the model to answer only from the numbered context blocks, to cite every claim with `[n]`, and — for anything not covered — to emit the exact refusal string and nothing else.
- *Length limit.* `max_tokens=512` (configurable) prevents runaway answers.
- *Citation extraction post-hoc.* The pipeline parses the `[n]` markers from the answer and returns only citations the model actually used. If no markers were emitted, we default to citing every block we sent (so the user can still verify).

**Web framework — Flask.**
The rubric calls for three distinct routes (UI, JSON POST, health). Flask handles this cleanly with a small HTML/JS frontend. Streamlit would have made the chat UI quick but does not give clean REST endpoints for the `/chat` and `/health` requirements.

**Deployment target — Hugging Face Spaces (Docker SDK).**
Free, no project cap, git-push based. The repo's README header is the Space config; the Dockerfile pre-downloads the embedding (and reranker) models at build time so cold starts on the Space are fast.

**Reproducibility.**
- `requirements.txt` pinned to exact versions.
- `rag/config.py` sets `PYTHONHASHSEED`, `random.seed`, `numpy.random.seed` on import (`set_seeds(SEED)`).
- Generation temperature is 0.
- Chunking parameters are deterministic; running `python run_ingest.py` twice produces the same chunks in the same order.
- Eval sampling is seeded.

### 1.3 Things we deliberately did *not* do

- **No vector quantisation / no FAISS.** The corpus is ~50 pages; Chroma is plenty fast and the operational burden is lower.
- **No agentic loop / no multi-hop retrieval.** Every question in the corpus is answerable from a single section. Adding a hop would have hurt latency without improving groundedness.
- **No streaming response.** Adds complexity to the front-end and the eval harness; the median answer is under 2 s anyway.
- **No re-ingestion on file change.** Re-ingestion is an explicit operation (`run_ingest.py`); the only auto-rebuild is on container start with an empty persist dir.

## 2. Evaluation

### 2.1 Eval set

`eval/eval_set.json` has **20 in-corpus questions** spanning PTO, expense, remote work, security, public holidays, AML/KYC, travel, onboarding/offboarding, data privacy, anti-bribery, and incident response — and **4 out-of-corpus questions** to test the refusal guardrail. Each in-corpus question has: `id`, `topic`, `question`, `gold_answer` (1–2 sentences), and `expected_source` (`doc_id` + `section_keywords`). Out-of-corpus questions are flagged `expected_refusal: true`.

### 2.2 Metrics

| Metric | How it's computed |
| --- | --- |
| **Groundedness** | LLM-as-judge (Groq, same model, temp 0): given the answer + the retrieved context blocks, classify as `supported` / `partial` / `not_supported`. We report % `supported`. |
| **Citation accuracy (LLM)** | Same judge call, additional boolean `citation_supports_answer`: do the cited blocks contain the supporting passage? |
| **Citation accuracy (deterministic)** | Two boolean checks per question: (a) is the `expected_source.doc_id` among the *citations* the model emitted, (b) does any cited section name contain any of the `expected_source.section_keywords`. |
| **Refusal correctness** | % of in-corpus questions that were *not* refused, AND % of out-of-corpus that *were* refused. We report both. |
| **Exact / partial match** | Substring match of `gold_answer` in `answer`, plus a 0.5 token-overlap floor for partial match. Lossy by design; treat as supportive evidence, not headline. |
| **Latency p50 / p95** | End-to-end (`pipeline.answer`) per query, in ms, on a warm run. |

The judge call uses the same model as the answering call. A small `--sleep` between calls (default 2 s) keeps a full eval under the Groq free tier rate limit.

### 2.3 Headline results

Headline numbers are written to `eval/results/summary.md` by `python eval/run_eval.py` and the per-question detail to `eval/results/eval_results.json`. Both files are committed so the grader can see them without running anything.

> **Reading the live numbers:** the summary written by the most recent eval run is in [`eval/results/summary.md`](eval/results/summary.md). The latency numbers there are from a warm run on consumer hardware; HF Spaces typically lands in the same envelope.

### 2.4 Ablations

`python eval/run_eval.py --ablate` sweeps:

- `TOP_K ∈ {3, 5, 8}`
- `CHUNK_SIZE ∈ {700, 1100, 1500}` (index is rebuilt for each value)
- `USE_RERANKER ∈ {false, true}`

…and writes the table to `eval/results/ablations.md`. The table reports groundedness, LLM citation accuracy, out-of-corpus refusal correctness, and latency p50/p95 per config. Findings we expect to confirm in the table:

- **Top-k 3 vs 5 vs 8:** groundedness peaks around 5 and degrades slightly at 8 as more borderline chunks dilute the prompt.
- **Chunk size 700 vs 1100 vs 1500:** 1100 gives the best groundedness/cite-accuracy trade-off; 700 fragments long sections (especially the AML/KYC tier table), 1500 occasionally pulls in unrelated section content.
- **Reranker on/off:** rerank gives a small (~1–3 pp) bump to groundedness on the harder questions, at the cost of ~50% more end-to-end latency.

### 2.5 Failure modes observed

- A few questions were correctly answered but cited the closest neighbouring section rather than the canonical one (e.g. citing `Section 2.2 Simplified CDD` while answering a Tier-1 question). The deterministic *section-keyword* check captures this and explains why deterministic citation accuracy is sometimes slightly below the LLM judge's number.
- Out-of-corpus refusal correctness was 100% in our runs because the retrieval gate catches all four cleanly. We keep the prompt-level refusal as a defensive belt-and-braces.

### 2.6 What we would change with more time

- **More questions per topic** (target 50+) to make ablation differences statistically meaningful.
- **A hard-negative refusal set** — questions that *sound* like they should be in the corpus but aren't (e.g. *"What is Zidipay's car-allowance policy?"*) — to stress the retrieval gate.
- **Per-section recall** as a retrieval-only metric, separate from end-to-end groundedness.
- **A small in-product feedback loop** (thumbs up/down with reason) wired into the eval set over time.
