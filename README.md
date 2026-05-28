---
title: Zidipay Policy RAG
emoji: 💬
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Zidipay Policy RAG

A small Retrieval-Augmented Generation (RAG) web app that answers questions about the policies and procedures of **Zidipay Financial Technologies**, a fictional East-African digital payments and mobile wallet company. The corpus is 100% synthetic.

Stack: **Python 3.11 · LangChain · Groq (Llama-3.3-70B) · HuggingFace bge-small embeddings · Chroma · Flask · Docker (Hugging Face Spaces)**.

## What it does

- Loads 14 policy documents in mixed formats (Markdown, HTML, PDF, TXT).
- Header-aware chunking, local embeddings, persisted Chroma index.
- Top-k retrieval (with optional cross-encoder reranker).
- Answers with **inline `[n]` citations** that link back to the source documents and a short snippet of the supporting chunk.
- Refuses out-of-corpus questions using a retrieval-score gate plus a system-prompt instruction.
- Ships with a Flask chat UI, JSON `/chat` API, and `/health` endpoint.
- Includes an evaluation harness measuring groundedness, citation accuracy, refusal correctness, exact/partial match, and latency p50/p95, plus ablations over `top_k`, `chunk_size`, and `reranker`.

## Architecture

```
                            ┌──────────────┐
   user question  ───────▶  │   Flask /chat │
                            └──────┬───────┘
                                   ▼
                       ┌───────────────────────┐
                       │  retrieve(top_k=5)    │  Chroma + bge-small embeddings
                       │  + score gate         │  (+ optional cross-encoder rerank)
                       └──────────┬────────────┘
                                  ▼
                       ┌───────────────────────┐
                       │ build prompt with      │
                       │ numbered [n] context   │  system prompt: answer only
                       └──────────┬────────────┘   from context, always cite,
                                  ▼                 refuse if no support
                       ┌───────────────────────┐
                       │     ChatGroq           │  llama-3.3-70b-versatile
                       │     temperature=0      │
                       └──────────┬────────────┘
                                  ▼
                       ┌───────────────────────┐
                       │ parse [n] → Citation   │  doc_id · title · section
                       │ list and snippets      │  · source · snippet
                       └───────────────────────┘
```

## Repository layout

```
zidipay-policy-rag/
├── app.py                       # Flask: /, /chat, /health, /source/<doc_id>
├── run_ingest.py                # CLI: build/rebuild the Chroma index
├── rag/
│   ├── config.py                # env + seeds
│   ├── loaders.py               # md/html/pdf/txt → Document
│   ├── ingest.py                # chunk → embed → persist (Chroma)
│   ├── retriever.py             # similarity + optional reranker
│   ├── generate.py              # prompt + Groq + guardrails + citations
│   └── pipeline.py              # answer(question) -> {answer, citations, ...}
├── corpus/                      # 14 policy docs (md/html/pdf/txt)
├── data/chroma/                 # persisted index (gitignored)
├── eval/
│   ├── eval_set.json            # 20 in-corpus + 4 out-of-corpus
│   ├── run_eval.py              # metrics + optional ablation sweep
│   └── results/                 # summary.md, eval_results.json, ablations.md
├── templates/index.html         # chat UI
├── static/style.css             # styling
├── tests/                       # pytest tests (offline)
├── .github/workflows/ci.yml     # build + test + optional HF Spaces deploy
├── Dockerfile                   # HF Spaces (Docker SDK)
├── requirements.txt
├── design-and-evaluation.md
├── ai-tooling.md
└── deployed.md
```

## Setup

```bash
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit and add your GROQ_API_KEY
```

The PDF policies in `corpus/` are checked in. If you ever need to regenerate them from text, run:

```bash
python scripts/generate_pdfs.py
```

## Run locally

```bash
python run_ingest.py     # builds the Chroma index from corpus/
python app.py            # starts Flask on http://localhost:5000
```

Open `http://localhost:5000` and ask a question like *"How many days of annual leave do I get?"*

The first run will download the embedding model (`BAAI/bge-small-en-v1.5`, ~130 MB) into the HuggingFace cache.

## API

- `GET /health` → `{"status":"ok","model":"...","index_chunks":N}`
- `POST /chat` with JSON `{"question": "..."}` → `{"answer", "citations":[{doc_title, section, snippet, source}], "latency_ms", "refused"}`
- `GET /source/<doc_id>` → serves the raw corpus document, so citation links open it directly.

## Evaluation

```bash
python eval/run_eval.py            # writes eval/results/summary.md + eval_results.json
python eval/run_eval.py --ablate   # writes eval/results/ablations.md + ablations.json
python eval/run_eval.py --limit 3  # quick smoke test (3 in-corpus + 1 out-of-corpus)
```

The harness runs every in-corpus question through the live pipeline, has an LLM-as-judge score groundedness and whether the cited sources actually support the answer, runs a deterministic check that the expected document and section keyword appear in the retrieved chunks, checks refusal correctness on the 4 out-of-corpus questions, and reports latency p50 / p95 over the in-corpus runs. Headline numbers and the per-question detail are committed under `eval/results/`.

## Tests

```bash
pytest -q
```

Tests use a tiny in-memory fixture corpus and a stubbed Groq call, so they run offline and don't need a real API key.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | *(required at runtime)* | Groq API key for the LLM. |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model. Fallback: `llama-3.1-8b-instant`. |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | HuggingFace embeddings model (local). |
| `USE_RERANKER` | `false` | Toggle cross-encoder reranker. |
| `TOP_K` | `5` | Number of chunks the LLM sees. |
| `K_FETCH` | `15` | Number of candidates fetched before rerank/cutoff. |
| `CHUNK_SIZE` | `1100` | Recursive splitter chunk size (chars). |
| `CHUNK_OVERLAP` | `150` | Recursive splitter overlap. |
| `MAX_OUTPUT_TOKENS` | `512` | Generation length cap. |
| `SCORE_THRESHOLD` | `0.30` | Min top-1 similarity; below → refusal. |
| `CHROMA_DIR` | `data/chroma` | Chroma persist directory. |
| `CORPUS_DIR` | `corpus` | Source documents. |
| `SEED` | `42` | RNG seed for reproducibility. |
| `PORT` | `5000` (local) / `7860` (Docker) | HTTP port. |

## Reproducibility

- All RNGs (`PYTHONHASHSEED`, `random`, `numpy.random`) are seeded from `SEED=42` in `rag/config.py` at import time.
- `temperature=0` for both the answering LLM and the LLM-judge in eval.
- Chunking parameters are deterministic.
- `requirements.txt` is fully pinned.
- The index rebuilds from `corpus/` on a fresh container — no binary artefacts in git.

## Deployment

The app is built to deploy on **Hugging Face Spaces (Docker SDK)**. The repo header at the top of this README is what HF Spaces reads to configure the Space. Set `GROQ_API_KEY` as a Space secret. The CI workflow can optionally push to the Space on every green merge to `main` if you add `HF_TOKEN` and `HF_SPACE_ID` as GitHub Actions secrets.

When deployed, the public URL goes in [`deployed.md`](deployed.md).

## Notes / assumptions

- Zidipay is fictional. All policy contents, figures, contacts, and document IDs are invented but kept internally consistent.
- The cross-encoder reranker is off by default (CPU-only deployments). Turn it on with `USE_RERANKER=true` and expect ~50% more latency per query.
- The Groq free tier is rate-limited; the eval harness inserts a short sleep between calls. If you hit the cap, switch `GROQ_MODEL` to `llama-3.1-8b-instant`.
