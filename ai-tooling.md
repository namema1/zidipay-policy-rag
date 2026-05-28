# AI Tooling

How AI tools were used to scope, design, and build this project.

## 1. Tools used

- **Claude (chat)** — for brainstorming the problem, deciding the architecture, choosing the tech stack, and writing the spec.
- **Claude Code (CLI agent)** — for building the entire repo from that spec: scaffolding directories, generating the synthetic corpus, writing the loader/ingest/retriever/generate/pipeline modules, the Flask app and front-end, the evaluation harness, the tests, the Dockerfile, the CI workflow, and the documentation.

## 2. What was done in chat

The chat session produced:

- A one-page **architecture decision record** (the choices in `design-and-evaluation.md` §1.2 came from this).
- A **rubric-to-deliverable mapping** so nothing in the brief would get missed.
- The **synthetic company brief** for Zidipay Financial Technologies — fictional but internally consistent (HQ in Nairobi, offices in Kenya/Uganda/Tanzania/Rwanda, KES as the primary currency, 24 days annual leave, KES 8,000 client-dinner cap, etc.).
- The **prompt for Claude Code** (`PROMPT.md`) — a single, exhaustive, sectioned brief covering the corpus, every code module, the eval harness, the CI workflow, the Dockerfile, the docs, and the working method. Front-loading the prompt with all of that meant Claude Code could work in long, mostly-uninterrupted stretches.

## 3. What was done in Claude Code

Claude Code was given the prompt and the `.env` (with the Groq API key) and built the project end-to-end:

- Created the directory structure and the pinned `requirements.txt`.
- Generated the 14 synthetic policy documents in mixed formats (9 markdown, 2 HTML, 2 PDF, 1 plain text), all internally consistent.
- Wrote every Python module under `rag/`: config + seeds, multi-format loaders, header-aware ingestion, retrieval with an optional cross-encoder reranker, prompt building + Groq call + citation parsing + guardrails, and a clean `pipeline.answer()` API.
- Wrote the Flask app, the chat UI (vanilla HTML/CSS/JS, no framework), and the source-document viewer route.
- Wrote `eval/eval_set.json` and `eval/run_eval.py` with all four required metric families and the ablation sweep flag.
- Wrote the offline pytest suite (`tests/`).
- Wrote the GitHub Actions CI workflow (build + test + optional HF Spaces deploy gated on secrets).
- Wrote the Dockerfile that pre-downloads the embedding and reranker models at build time so HF Space cold starts are fast.
- Wrote this document, the README, and `design-and-evaluation.md`.

## 4. What worked well

- **Pre-deciding the architecture in chat.** Going into Claude Code with the LLM/embeddings/vector-store/framework decisions already made meant zero churn on those choices during the build — every module dropped into the right shape on the first attempt.
- **A single exhaustive prompt.** The `PROMPT.md` document is long, but writing it once was much cheaper than dripping requirements in turn-by-turn. Claude Code re-read the prompt as a checklist.
- **Front-loading reproducibility.** Pinning `requirements.txt`, seeding RNGs at config import time, and using `temperature=0` for both the answer model and the LLM judge — all decided up front — meant the eval results were reproducible across runs.
- **Header-aware chunking.** Deciding *early* that citations would be `doc_title — section` (not just `doc_title`) shaped the loader/ingest metadata, the retriever's score gate, the prompt format, and the front-end card all at once. One decision, four files.

## 5. What needed iteration

- **Citation extraction post-hoc.** The first cut had the model emit a JSON sidecar with citations; that was brittle. The final design is much simpler — let the model emit `[n]` markers in plain prose, then parse them out — and it survives the model occasionally being chatty about its sources.
- **Score normalisation across retrieval modes.** Chroma returns a distance, not a similarity, and the cross-encoder returns an unbounded logit. We normalise both into `[0,1]` so a single `SCORE_THRESHOLD` works regardless of `USE_RERANKER`, which keeps the refusal gate honest.
- **Deterministic vs LLM-judge citation accuracy.** The deterministic check (expected `doc_id` + section-keyword in the citation) was added after seeing the LLM judge accept answers whose citation pointed at a neighbouring section. Both numbers are reported so the trade-off is visible.

## 6. Things to remember if rebuilding from scratch

- Decide the **citation shape** before writing the loader. It defines the metadata you need to carry through chunking.
- Decide the **refusal contract** before writing the prompt. It defines the test you can write before the LLM is wired up.
- Pin **everything** — including `transformers`, `torch`, and `chromadb` — before the first ingest. Otherwise an upstream patch release can quietly shift the chunking or embedding behaviour, and your eval becomes non-reproducible.
- Stub the LLM in tests. A real Groq call in CI is both slow and fragile.
