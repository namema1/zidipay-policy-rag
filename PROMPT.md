# CLAUDE CODE PROMPT — paste this entire file as your first message

You are building a complete, production-quality **Retrieval-Augmented Generation (RAG)** web application for a graded Masters AI-engineering project. Build it end to end: synthetic corpus → ingestion/indexing → RAG pipeline → Flask web app → guardrails → evaluation harness → tests → CI/CD → all required docs. Work incrementally, run things as you go, and make sure the app actually runs and the tests pass before you finish. Use **LangChain** for orchestration.

## Fictional company
The corpus belongs to **Zidipay Financial Technologies**, a fictional East-African digital payments & mobile wallet company (markets: Kenya, Uganda, Tanzania, Rwanda). Everything is synthetic — invent realistic but fictional details. Be consistent across documents (same leave allowances, same currency KES/USD, same office locations).

## Tech stack (use exactly these)
- Python 3.11
- LangChain (`langchain`, `langchain-community`, `langchain-groq`, `langchain-huggingface`, `langchain-chroma`, `langchain-text-splitters`)
- LLM: **Groq** via `langchain-groq`, model from env `GROQ_MODEL` (default `llama-3.3-70b-versatile`), temperature **0**
- Embeddings: **local** `HuggingFaceEmbeddings`, model from env `EMBEDDING_MODEL` (default `BAAI/bge-small-en-v1.5`) — no API key, deterministic
- Vector store: **Chroma**, persisted to `data/chroma/`
- Optional re-ranker: `sentence-transformers` cross-encoder `cross-encoder/ms-marco-MiniLM-L-6-v2`, toggled by env `USE_RERANKER`
- Web: **Flask** + minimal vanilla HTML/CSS/JS frontend
- PDF parsing: `pypdf`; HTML parsing: `beautifulsoup4`/`unstructured` or LangChain's HTML loader
- For generating the PDF corpus files: `reportlab` (or `fpdf2`)
- Tests: `pytest`

Pin all versions in `requirements.txt`.

## Project structure (create exactly this)
```
zidipay-policy-rag/
├── app.py                      # Flask: /, /chat (POST), /health (GET), /source/<id>
├── run_ingest.py               # CLI: build/rebuild the Chroma index from corpus/
├── rag/
│   ├── __init__.py
│   ├── config.py               # env settings + seed setting (PYTHONHASHSEED, random, numpy)
│   ├── loaders.py              # load md/html/pdf/txt with metadata
│   ├── ingest.py               # clean → chunk (header-aware) → embed → persist to Chroma
│   ├── retriever.py            # Chroma retrieval (top-k, k_fetch) + optional cross-encoder rerank
│   ├── generate.py             # prompt build, Groq call, guardrails, citation extraction
│   └── pipeline.py             # answer(question) -> {answer, citations, contexts, latency_ms, refused}
├── corpus/                     # the generated policy docs (mixed formats)
├── data/chroma/                # persisted index (gitignored; rebuilt on startup if empty)
├── eval/
│   ├── eval_set.json           # 20 in-corpus Q + 4 out-of-corpus Q, with gold answers & expected sources
│   ├── run_eval.py             # runs pipeline, computes metrics, writes results
│   └── results/                # eval_results.json, summary.md, ablations.md (committed)
├── templates/index.html        # chat UI
├── static/style.css            # styling
├── tests/
│   ├── test_health.py
│   ├── test_import.py
│   ├── test_ingest.py          # builds a tiny index from a fixture
│   ├── test_retrieval.py       # retrieval returns chunks with source metadata
│   └── test_pipeline.py        # in-corpus returns citations; out-of-corpus refuses
├── .github/workflows/ci.yml
├── Dockerfile                  # for HF Spaces Docker deploy
├── requirements.txt
├── .env.example
├── .gitignore
├── Makefile                    # setup, ingest, run, eval, test targets
├── README.md
├── design-and-evaluation.md
├── ai-tooling.md
└── deployed.md                 # placeholder for the deployed URL
```

## Step 1 — Generate the corpus (`corpus/`)
Create **14 documents**, mixed formats, totalling roughly 40–70 pages. Make them realistic, internally consistent, with clear markdown headings/sections (sections matter for citations). Each document starts with a title (H1) and an `Effective date` / `Document ID` line.

Formats — deliberately mix to prove the loaders handle all four:
- **Markdown (.md)** — 9 files
- **HTML (.html)** — 2 files (well-formed, with headings)
- **PDF (.pdf)** — 2 files (generate with reportlab/fpdf2 from text you write; multi-page, with headings)
- **TXT (.txt)** — 1 file

Documents to create (invent specific, consistent figures):
1. `employee-handbook.md` — overview, mission, working hours, conduct summary
2. `pto-and-leave-policy.md` — annual leave days, sick leave, parental leave, carry-over, how to request
3. `remote-and-hybrid-work-policy.md` — eligibility, days in office, equipment, security expectations
4. `information-security-policy.md` — passwords/MFA, data classification, acceptable use, incident reporting
5. `acceptable-use-and-device-policy.html` — devices, BYOD, prohibited use
6. `data-protection-and-privacy-policy.html` — Kenya DPA / GDPR-style principles, data subject rights, retention
7. `expense-and-reimbursement-policy.md` — per-diems, meal/client-dinner limits, approval thresholds, submission process
8. `travel-policy.md` — booking, classes of travel, advances
9. `aml-kyc-policy.pdf` — customer due diligence, KYC tiers, transaction monitoring, reporting (fintech-specific)
10. `anti-bribery-and-code-of-conduct.pdf` — gifts, conflicts of interest, sanctions
11. `performance-review-and-promotion-policy.md` — cycles, ratings, promotion criteria
12. `onboarding-and-offboarding-procedure.md` — step-by-step procedures, access provisioning/revocation
13. `incident-response-and-business-continuity.md` — severity levels, escalation, RTO/RPO
14. `public-holidays-and-working-hours.txt` — East-African public holidays, core hours, overtime

## Step 2 — Config & reproducibility (`rag/config.py`)
- Load env via `python-dotenv`. Expose: `GROQ_API_KEY`, `GROQ_MODEL`, `EMBEDDING_MODEL`, `USE_RERANKER` (bool), `TOP_K` (int, default 5), `K_FETCH` (int, default 15), `CHUNK_SIZE` (default 1100), `CHUNK_OVERLAP` (default 150), `MAX_OUTPUT_TOKENS` (default 512), `SCORE_THRESHOLD` (refusal gate), `CHROMA_DIR`, `CORPUS_DIR`, `SEED` (default 42).
- A `set_seeds()` function setting `PYTHONHASHSEED`, `random.seed`, `numpy.random.seed`. Call it on import.

## Step 3 — Loaders (`rag/loaders.py`)
- Load each file type with the appropriate LangChain loader (md/txt as text, HTML via BSHTMLLoader/UnstructuredHTMLLoader, PDF via PyPDFLoader).
- Clean text (strip excess whitespace, drop boilerplate).
- Attach metadata to every Document: `source` (filename), `doc_title` (the H1), `doc_id`.

## Step 4 — Ingestion (`rag/ingest.py`, `run_ingest.py`)
- Header-aware chunking: `MarkdownHeaderTextSplitter` to split on `#`/`##`/`###` (carry section titles into metadata), then `RecursiveCharacterTextSplitter` (CHUNK_SIZE/CHUNK_OVERLAP) for oversized sections. For HTML/PDF/TXT without markdown headers, fall back to `RecursiveCharacterTextSplitter`.
- Each chunk's metadata: `doc_id`, `doc_title`, `source`, `section` (heading path), `chunk_id`.
- Embed with the configured local HF embeddings; persist to Chroma at `CHROMA_DIR`.
- `run_ingest.py`: deletes & rebuilds the index; prints chunk count. Make chunking deterministic.

## Step 5 — Retrieval (`rag/retriever.py`)
- `retrieve(query) -> list[(Document, score)]`: similarity search fetching `K_FETCH`, then if `USE_RERANKER`, run the cross-encoder over the candidates and keep top `TOP_K`; else keep top `TOP_K` by similarity.
- Expose the best similarity score for the refusal gate.

## Step 6 — Generation & guardrails (`rag/generate.py`)
- Build a prompt that injects the retrieved chunks as **numbered, labelled context** (each labelled with `doc_title — section`).
- System prompt enforces: answer ONLY from the provided context; cite the source(s) for every claim using the section labels; be concise (respect length limit); if the context does not contain the answer, reply exactly with the refusal message `"I can only answer questions about Zidipay's policies and procedures."`
- **Refusal gate:** if best retrieval score is below `SCORE_THRESHOLD` (or no chunks), return the refusal without calling the LLM.
- Call Groq (`ChatGroq`, temperature 0, `max_tokens=MAX_OUTPUT_TOKENS`).
- Parse/return structured **citations**: list of `{doc_id, doc_title, section, source, snippet}` drawn from the chunks actually used. `snippet` = a short excerpt of the supporting chunk.

## Step 7 — Pipeline (`rag/pipeline.py`)
- `answer(question) -> {answer, citations, contexts, latency_ms, refused}`. Time the full request→answer span for the latency metric.

## Step 8 — Flask app (`app.py`)
- `GET /` → renders `templates/index.html` (a clean chat box; on submit, POSTs to `/chat` via fetch and renders answer + citations with clickable source links + snippets).
- `POST /chat` → body `{"question": "..."}`; returns JSON `{answer, citations:[{doc_title, section, snippet, source}], latency_ms, refused}`. Each citation links to `/source/<doc_id>`.
- `GET /health` → JSON `{"status":"ok","model":<GROQ_MODEL>,"index_chunks":<n>}`.
- `GET /source/<doc_id>` → serves the raw corpus document so citation links work.
- **On startup**, if the Chroma index is empty/missing, run ingestion automatically (so fresh deploys self-build).
- Read host/port from env (`PORT`, default 5000) and bind `0.0.0.0` for deployment.
- Use the frontend-design skill for a polished, non-generic UI (clean typography, the citations clearly shown under each answer). Do NOT use browser localStorage/sessionStorage.

## Step 9 — Evaluation (`eval/eval_set.json`, `eval/run_eval.py`)
- `eval_set.json`: **20 in-corpus questions** spanning PTO, security, expense, remote/hybrid, public holidays, AML/KYC, travel, onboarding/offboarding, data privacy, whistleblowing — each with `id`, `question`, `gold_answer` (1–2 sentence), `expected_source` (doc_id + section), `topic`. Plus **4 out-of-corpus questions** flagged `expected_refusal: true`.
- `run_eval.py` computes and reports:
  - **Groundedness** (%): LLM-as-judge (Groq, temp 0) — given answer + retrieved contexts, is the answer fully supported? Return supported/not + reason.
  - **Citation accuracy** (%): (a) LLM judge that the cited sources support the answer, AND (b) a deterministic check that each cited doc/section was among the retrieved contexts. Report both.
  - **Refusal correctness** (%): out-of-corpus questions correctly refused; in-corpus not refused.
  - **Exact/Partial match** (%, optional): token-overlap / substring vs `gold_answer`.
  - **Latency p50/p95** (ms) over the in-corpus queries (warm run).
- Add a small delay between Groq calls to respect free-tier rate limits.
- Write `eval/results/eval_results.json` (per-question) and `eval/results/summary.md` (headline table). **Commit these results.**
- **Ablations** (`--ablate` flag → `eval/results/ablations.md`): sweep `TOP_K ∈ {3,5,8}`, `CHUNK_SIZE ∈ {700,1100,1500}`, and `USE_RERANKER ∈ {false,true}`; report groundedness + latency per config in a table. Seed eval sampling.

## Step 10 — Tests (`tests/`)
Lightweight, runnable in CI without network where possible:
- `test_import.py`: `import app` succeeds.
- `test_health.py`: Flask test client → `/health` returns 200 + `status:ok`.
- `test_ingest.py`: build a tiny index from a 2-doc fixture; assert chunks created with required metadata.
- `test_retrieval.py`: a fixture query returns ≥1 chunk with `doc_title`/`section` metadata.
- `test_pipeline.py`: monkeypatch/stub the Groq call so it runs offline; assert an in-corpus question returns citations and an out-of-corpus question returns the refusal string.
Make tests not require a real GROQ key (stub the LLM); CI runs them offline.

## Step 11 — CI/CD (`.github/workflows/ci.yml`)
On `push` and `pull_request`:
- `build` job: checkout → setup Python 3.11 → `pip install -r requirements.txt` → import check `python -c "import app"` → `pytest -q`.
- `deploy` job (runs only on `push` to `main`, `needs: build`): push the repo to a Hugging Face Space using secrets `HF_TOKEN` and `HF_SPACE_ID` (git push to the Space remote). Guard it so it's skipped gracefully if secrets are absent.

## Step 12 — Dockerfile
- Python 3.11 slim base. Install requirements. **Pre-download** the embedding + reranker models at build time (so cold starts are fast). Expose `PORT`. Start the app with gunicorn (`gunicorn -b 0.0.0.0:$PORT app:app`) — and ensure startup ingestion runs. Add a Hugging Face Spaces header comment block at the top of `README.md` (`title`, `sdk: docker`, `app_port`) so the Space configures itself.

## Step 13 — Docs
- `README.md`: project summary; HF Spaces config header; architecture diagram (ASCII or mermaid); setup (venv, `pip install -r requirements.txt`, `.env`); run (`python run_ingest.py`, `python app.py`); how to run eval and tests; env var table; **fixed-seed note**.
- `design-and-evaluation.md`: (i) design & architecture decisions and **why** (embedding model, chunking strategy, k, prompt format, vector store, framework, deployment) — use the rationale from the project plan; (ii) evaluation approach + the actual results (groundedness, citation accuracy, latency p50/p95, ablation summary).
- `ai-tooling.md`: describe that brainstorming/architecture was done in Claude chat and the build in Claude Code; note what worked well and what needed iteration.
- `.env.example`: all env vars with safe defaults (no real key).
- `.gitignore`: `.env`, `data/chroma/`, `__pycache__/`, venv, model caches.
- `Makefile`: `setup`, `ingest`, `run`, `eval`, `test`.
- `deployed.md`: placeholder line for the public URL.

## Working method
1. Scaffold structure + `requirements.txt` + config first.
2. Generate the corpus.
3. Build loaders → ingest → run `run_ingest.py` and confirm chunk count.
4. Build retriever → generate → pipeline; smoke-test `answer()` on 2 sample questions.
5. Build Flask app; run it and confirm `/`, `/chat`, `/health`, `/source/<id>`.
6. Write eval set + harness; run a quick eval (you can stub Groq if no key) and write results.
7. Write tests; run `pytest -q` until green.
8. Write CI workflow, Dockerfile, and all docs.
9. Final check: fresh `pip install -r requirements.txt`, `python run_ingest.py`, `python app.py`, `pytest -q` all succeed. Report a summary of what you built and any TODOs for me.

Ask me nothing unless genuinely blocked — make reasonable assumptions, keep them consistent, and note them in the README.
