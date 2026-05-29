# AI Tooling

How AI tools were used to scope, design, build, and debug this project. This document is honest and specific — every claim below corresponds to work actually done.

## 1. Tools used

- **Claude.ai (chat)** — for brainstorming the problem, choosing the stack, deciding the architecture, mapping the rubric to deliverables, and writing the exhaustive prompt that drove Claude Code.
- **Claude Code (agentic CLI / IDE coder)** — for generating the entire codebase from that prompt, and for the subsequent diagnosis and debugging iteration when the first eval surfaced issues.

## 2. What was done in Claude.ai (chat)

The chat sessions were used as a thinking partner before any code was written. Concrete outputs:

- **Architecture decisions.** Walking through tradeoffs and converging on a single defensible choice for each axis: Flask vs Streamlit (rubric needs `/chat` POST and `/health` JSON alongside the UI — Flask wins cleanly); LangChain as the orchestration layer; Groq `llama-3.3-70b-versatile` as the LLM (free tier, GPT-4o-class quality, low latency, open-source); local `BAAI/bge-small-en-v1.5` embeddings (no API key, no rate limits, deterministic, small image); Chroma as the local persisted vector store (zero external services); Hugging Face Spaces (Docker SDK) as the deploy target (free, no project cap, git-push deployable).
- **Synthetic company brief.** The Zidipay backstory — fictional East African digital payments company headquartered in Nairobi with offices across Kenya, Uganda, Tanzania, and Rwanda; KES as the primary currency; internally-consistent numbers (24 days annual leave, KES 8,000 client-dinner cap, etc.). Establishing this upfront kept the 14 policy documents internally consistent.
- **Prompt engineering for Claude Code.** Drafting PROMPT.md — a single, exhaustive, sectioned brief covering the corpus, every code module, the eval harness, the CI/CD workflows, the Dockerfile, the docs, and the working method. Front-loading the prompt with all of that meant Claude Code could work in long, mostly-uninterrupted stretches and treat the prompt as a self-contained checklist.

**What worked in chat:** rapid alignment on stack tradeoffs with rubric traceability — every architectural choice could be defended in terms of a specific rubric item it satisfied. The chat surfaced second-order consequences (e.g. "if citations are `doc — section` instead of just `doc`, the loader needs to carry section metadata, which forces header-aware chunking, which affects the whole chunking strategy") before they showed up as code-level rework.

## 3. What was done in Claude Code

Claude Code was given PROMPT.md plus a `.env` containing the Groq API key, and built the project end-to-end:

- Pinned `requirements.txt` and the project directory structure.
- The 14 synthetic policy documents in mixed formats: 9 Markdown, 2 HTML, 2 PDF (generated with `reportlab` / `fpdf2`), 1 plain text. All internally consistent with the Zidipay brief.
- Every Python module under `rag/`: `config.py` (env + seeds), `loaders.py` (md/html/pdf/txt → Document), `ingest.py` (chunk → embed → persist Chroma), `retriever.py` (similarity + optional cross-encoder rerank), `generate.py` (prompt + Groq + citation parsing + guardrails), `pipeline.py` (`answer(question)` API).
- The Flask app, the chat UI (vanilla HTML/CSS/JS — no framework), and the `/source/<doc_id>` route that serves raw corpus files.
- The evaluation harness ([eval/run_eval.py](eval/run_eval.py)) with all four required metric families (groundedness, citation accuracy, refusal correctness, latency) plus the ablation sweep flag.
- The offline pytest suite under `tests/`, with a stubbed Groq call so CI never depends on a real API key.
- The split CI/CD workflows (`ci.yml` for build + tests, `cd.yml` for HF Space deploy via `workflow_run`).
- The Dockerfile that builds the Chroma index into the image and uses `/tmp` as the writable persist directory at runtime.
- The initial drafts of this document, the README, and `design-and-evaluation.md`.

**What worked well:**

- The step-by-step working method in PROMPT.md kept Claude Code incremental and self-verifying — it ran imports, ran the index build, and ran the test suite as it went, instead of producing one giant unverified diff.
- Front-loading reproducibility (pinned deps, seeded RNGs at config import time, `temperature=0` for both the answer model and the LLM judge) meant eval numbers were stable across runs without retrofitting.

**What needed iteration:**

- **Initial eval used placeholder numbers.** The first commit landed the harness with stub results in the summary file. The first real run produced real numbers but also surfaced a real failure (see below).
- **TOP_K=5 was wrong for this corpus.** The first real eval run refused on Q03 (parental leave). Diagnosis in Claude Code: inspected the per-question JSON, saw the right document was in `contexts` but the parental-leave section was clipped; re-ran retrieval with a higher `k` and confirmed the canonical chunk was at rank 8. Fix: bumped `TOP_K` to 8 in [.env.example](.env.example) and on the deployed Space. This was a follow-up Claude Code session and is exactly the kind of data-driven config change the agentic loop is good at — see, diagnose, change, re-verify, in one session.
- **HF Spaces read-only filesystem.** The first deploy crashed trying to write Chroma into the image directory. Fix in a follow-up Claude Code iteration: pre-build the index into the image at Docker build time and switch the runtime persist path to `/tmp`.

## 4. Honest assessment

- **Code architecture and tooling were stable on first generation.** Claude Code produced a working repo from PROMPT.md without architectural rework. The bugs that needed fixing were operational (TOP_K window, deploy filesystem) rather than structural.
- **Real eval numbers required real runs, not generation.** The placeholders in the first summary file were a giveaway that no Groq calls had actually been made yet. The honest result is what landed after the real eval, the Q03 diagnostic, and the TOP_K fix.
- **The reranker is built but not benchmarked on deployed hardware.** The code is complete and unit-tested; it just isn't part of the headline eval numbers in this submission.

## 5. Lessons worth keeping

- **Decide the citation shape before writing the loader.** It defines the metadata the loader has to carry through chunking, retrieval, and the prompt format. Changing it after the fact ripples through four files.
- **Decide the refusal contract before writing the prompt.** It lets you write the refusal test before the LLM is wired up, and it gives the score gate a concrete string to match against.
- **Pin every dependency including `transformers`, `torch`, and `chromadb` before the first ingest.** An upstream patch release can quietly shift chunking or embedding behaviour, and reproducibility quietly breaks.
- **Stub the LLM in tests.** A real Groq call in CI is both slow and fragile, and the Groq free tier rate limits will bite during PR storms.
- **Inspect the per-question JSON when a metric drops.** The TOP_K=5 refusal on Q03 was a one-minute fix because the eval harness wrote the contexts to disk; a black-box "groundedness = 95%" line would have taken much longer to diagnose.
