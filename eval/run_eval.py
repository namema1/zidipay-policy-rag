"""End-to-end evaluation harness for the Zidipay Policy RAG.

Metrics:
  - Groundedness (LLM-as-judge)
  - Citation accuracy (LLM judge + deterministic in-context check)
  - Refusal correctness
  - Exact / partial match vs gold_answer
  - Latency p50 / p95

Optionally runs ablations over TOP_K, CHUNK_SIZE, USE_RERANKER.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Ensure project root is on sys.path when invoked as `python eval/run_eval.py`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.messages import HumanMessage, SystemMessage

from rag.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    REFUSAL_MESSAGE,
    SEED,
    set_seeds,
)
from rag.pipeline import answer as rag_answer


EVAL_SET_PATH = ROOT / "eval" / "eval_set.json"
RESULTS_DIR = ROOT / "eval" / "results"
DEFAULT_SLEEP_BETWEEN_CALLS = 2.0  # seconds; Groq free tier is rate-limited


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2}


def token_overlap(answer: str, gold: str) -> float:
    a, g = _tokens(answer), _tokens(gold)
    if not g:
        return 0.0
    return len(a & g) / len(g)


def substring_match(answer: str, gold: str) -> bool:
    return (gold or "").strip().lower() in (answer or "").lower()


def is_refusal(answer: str) -> bool:
    if not answer:
        return False
    return REFUSAL_MESSAGE.lower().rstrip(".") in answer.lower()


def deterministic_citation_check(
    citations: list[dict], expected: dict | None, contexts: list[dict]
) -> dict:
    """Was the expected source among the retrieved contexts? Among the citations?"""
    expected_doc = (expected or {}).get("doc_id", "")
    keywords = [k.lower() for k in (expected or {}).get("section_keywords", [])]

    ctx_doc_ids = {c.get("doc_id") for c in contexts}
    cited_doc_ids = {c.get("doc_id") for c in citations}
    cited_sections = [(c.get("section") or "").lower() for c in citations]

    expected_doc_in_contexts = expected_doc in ctx_doc_ids if expected_doc else False
    expected_doc_in_citations = expected_doc in cited_doc_ids if expected_doc else False

    if not keywords or not cited_sections:
        keyword_hit = expected_doc_in_citations
    else:
        keyword_hit = any(
            any(k in section for k in keywords) for section in cited_sections
        )

    return {
        "expected_doc_in_contexts": bool(expected_doc_in_contexts),
        "expected_doc_in_citations": bool(expected_doc_in_citations),
        "expected_section_keyword_hit": bool(keyword_hit),
    }


# ---------------------------------------------------------------------------
# LLM judge
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """You are an evaluation judge for a RAG system. You will be given a question, an answer the system produced, and the context blocks the system retrieved.

You must respond with a single JSON object on one line and nothing else, with these keys:
- "groundedness": "supported" | "partial" | "not_supported"
- "citation_supports_answer": true | false
- "reason": short string

Definitions:
- "supported": every factual claim in the answer is fully supported by the context.
- "partial": some claims are supported and some are not.
- "not_supported": the answer is not supported by the context.
- "citation_supports_answer": true if the cited context block(s) actually contain the supporting passage for the answer.
Be strict but fair. Do not penalise paraphrasing; do penalise added facts not in the context.
"""


def _judge_llm():
    from langchain_groq import ChatGroq

    if not GROQ_API_KEY:
        return None
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0,
        max_tokens=200,
    )


def llm_judge(judge, question: str, answer: str, contexts: list[dict]) -> dict:
    if judge is None:
        return {
            "groundedness": "unknown",
            "citation_supports_answer": False,
            "reason": "judge_unavailable",
        }
    ctx = "\n\n".join(
        f"[{i+1}] {c.get('doc_title','')} — {c.get('section','')}\n{c.get('snippet','')}"
        for i, c in enumerate(contexts)
    )
    user = (
        f"Question: {question}\n\n"
        f"Answer:\n{answer}\n\n"
        f"Context:\n{ctx}\n\n"
        "Respond with the JSON object only."
    )
    try:
        resp = judge.invoke(
            [SystemMessage(content=JUDGE_SYSTEM), HumanMessage(content=user)]
        )
        text = (resp.content or "").strip()
        # Cope with code fences
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {
                "groundedness": "unknown",
                "citation_supports_answer": False,
                "reason": f"unparseable: {text[:80]}",
            }
        return json.loads(match.group(0))
    except Exception as e:  # pragma: no cover
        return {
            "groundedness": "unknown",
            "citation_supports_answer": False,
            "reason": f"judge_error: {e}",
        }


# ---------------------------------------------------------------------------
# Single-config run
# ---------------------------------------------------------------------------


@dataclass
class RunConfig:
    top_k: int | None = None
    chunk_size: int | None = None
    use_reranker: bool | None = None


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * q
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def _maybe_rebuild_for_chunk_size(chunk_size: int | None) -> None:
    """If chunk_size differs from default, rebuild the index. Used for ablations only."""
    if chunk_size is None:
        return
    from rag.config import CHUNK_SIZE
    from rag.ingest import build_index

    if chunk_size == CHUNK_SIZE:
        return
    print(f"  [ablate] rebuilding index with chunk_size={chunk_size}…")
    build_index(chunk_size=chunk_size, reset=True)


def run_once(
    eval_set: dict,
    sleep_s: float,
    cfg: RunConfig | None = None,
    rebuild_for_chunk_size: bool = False,
) -> dict:
    cfg = cfg or RunConfig()
    if rebuild_for_chunk_size:
        _maybe_rebuild_for_chunk_size(cfg.chunk_size)

    judge = _judge_llm()
    in_corpus = eval_set["in_corpus"]
    ooc = eval_set["out_of_corpus"]

    per_question = []
    latencies = []
    grounded_supported = 0
    grounded_partial = 0
    cite_llm_ok = 0
    cite_det_doc_ok = 0
    cite_det_kw_ok = 0
    refusal_correct_in = 0
    refusal_correct_out = 0
    em_count = 0
    partial_count = 0

    for q in in_corpus:
        result = rag_answer(
            q["question"],
            top_k=cfg.top_k,
            use_reranker=cfg.use_reranker,
        )
        latencies.append(result["latency_ms"])

        refused = result["refused"]
        if not refused:
            refusal_correct_in += 1

        det = deterministic_citation_check(
            result.get("citations", []), q.get("expected_source"), result.get("contexts", [])
        )
        if det["expected_doc_in_citations"]:
            cite_det_doc_ok += 1
        if det["expected_section_keyword_hit"]:
            cite_det_kw_ok += 1

        judge_result = (
            {"groundedness": "skipped", "citation_supports_answer": False, "reason": "refused"}
            if refused
            else llm_judge(judge, q["question"], result["answer"], result["contexts"])
        )
        if not refused:
            time.sleep(sleep_s)

        if judge_result.get("groundedness") == "supported":
            grounded_supported += 1
        elif judge_result.get("groundedness") == "partial":
            grounded_partial += 1
        if judge_result.get("citation_supports_answer"):
            cite_llm_ok += 1

        sub = substring_match(result["answer"], q["gold_answer"])
        overlap = token_overlap(result["answer"], q["gold_answer"])
        if sub:
            em_count += 1
            partial_count += 1
        elif overlap >= 0.5:
            partial_count += 1

        per_question.append(
            {
                "id": q["id"],
                "topic": q["topic"],
                "question": q["question"],
                "answer": result["answer"],
                "refused": refused,
                "latency_ms": result["latency_ms"],
                "gold_answer": q.get("gold_answer", ""),
                "expected_source": q.get("expected_source"),
                "citations": result["citations"],
                "deterministic_check": det,
                "judge": judge_result,
                "substring_match": sub,
                "token_overlap": overlap,
            }
        )

    for q in ooc:
        result = rag_answer(q["question"], top_k=cfg.top_k, use_reranker=cfg.use_reranker)
        refused = result["refused"] or is_refusal(result["answer"])
        if refused:
            refusal_correct_out += 1
        per_question.append(
            {
                "id": q["id"],
                "topic": q["topic"],
                "question": q["question"],
                "answer": result["answer"],
                "refused": refused,
                "latency_ms": result["latency_ms"],
                "expected_refusal": True,
                "citations": result["citations"],
            }
        )

    n_in = len(in_corpus)
    n_ooc = len(ooc)

    summary = {
        "n_in_corpus": n_in,
        "n_out_of_corpus": n_ooc,
        "groundedness_pct": round(100 * grounded_supported / max(n_in, 1), 1),
        "groundedness_with_partial_pct": round(
            100 * (grounded_supported + 0.5 * grounded_partial) / max(n_in, 1), 1
        ),
        "citation_accuracy_llm_pct": round(100 * cite_llm_ok / max(n_in, 1), 1),
        "citation_accuracy_deterministic_doc_pct": round(
            100 * cite_det_doc_ok / max(n_in, 1), 1
        ),
        "citation_accuracy_deterministic_keyword_pct": round(
            100 * cite_det_kw_ok / max(n_in, 1), 1
        ),
        "refusal_correct_in_pct": round(100 * refusal_correct_in / max(n_in, 1), 1),
        "refusal_correct_out_pct": round(100 * refusal_correct_out / max(n_ooc, 1), 1),
        "refusal_overall_pct": round(
            100 * (refusal_correct_in + refusal_correct_out) / max(n_in + n_ooc, 1), 1
        ),
        "substring_match_pct": round(100 * em_count / max(n_in, 1), 1),
        "partial_match_pct": round(100 * partial_count / max(n_in, 1), 1),
        "latency_p50_ms": round(_percentile(latencies, 0.5)),
        "latency_p95_ms": round(_percentile(latencies, 0.95)),
        "config": {
            "top_k": cfg.top_k,
            "chunk_size": cfg.chunk_size,
            "use_reranker": cfg.use_reranker,
        },
    }
    return {"summary": summary, "per_question": per_question}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def write_summary_md(summary: dict, path: Path) -> None:
    s = summary
    lines = [
        "# Zidipay Policy RAG — Evaluation Summary",
        "",
        f"- In-corpus questions: **{s['n_in_corpus']}**",
        f"- Out-of-corpus questions: **{s['n_out_of_corpus']}**",
        "",
        "## Information-quality metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Groundedness (fully supported, LLM judge) | **{s['groundedness_pct']}%** |",
        f"| Groundedness (with partial = 0.5) | {s['groundedness_with_partial_pct']}% |",
        f"| Citation accuracy (LLM judge) | **{s['citation_accuracy_llm_pct']}%** |",
        f"| Citation accuracy (deterministic, expected doc cited) | {s['citation_accuracy_deterministic_doc_pct']}% |",
        f"| Citation accuracy (deterministic, expected section keyword in citation) | {s['citation_accuracy_deterministic_keyword_pct']}% |",
        f"| Refusal correctness (in-corpus, not refused) | {s['refusal_correct_in_pct']}% |",
        f"| Refusal correctness (out-of-corpus, refused) | **{s['refusal_correct_out_pct']}%** |",
        f"| Refusal overall | {s['refusal_overall_pct']}% |",
        f"| Substring match vs gold answer | {s['substring_match_pct']}% |",
        f"| Partial match (substring or ≥0.5 token overlap) | {s['partial_match_pct']}% |",
        "",
        "## System metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Latency p50 | **{s['latency_p50_ms']} ms** |",
        f"| Latency p95 | **{s['latency_p95_ms']} ms** |",
        "",
        f"Config: `{json.dumps(s['config'])}`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_ablations_md(rows: list[dict], path: Path) -> None:
    lines = [
        "# Ablation Sweep",
        "",
        "Each row is a separate evaluation run. Index is rebuilt when `chunk_size` changes.",
        "",
        "| top_k | chunk_size | reranker | groundedness | citation (LLM) | refusal (out) | p50 ms | p95 ms |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        s = r["summary"]
        c = s["config"]
        lines.append(
            f"| {c['top_k']} | {c['chunk_size']} | {c['use_reranker']} | "
            f"{s['groundedness_pct']}% | {s['citation_accuracy_llm_pct']}% | "
            f"{s['refusal_correct_out_pct']}% | "
            f"{s['latency_p50_ms']} | {s['latency_p95_ms']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Zidipay RAG evaluation.")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_BETWEEN_CALLS)
    parser.add_argument(
        "--ablate", action="store_true", help="Run an ablation sweep and exit."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only run the first N in-corpus questions (for smoke tests).",
    )
    args = parser.parse_args(argv)

    set_seeds(SEED)
    random.seed(SEED)

    if not EVAL_SET_PATH.exists():
        print(f"Eval set not found at {EVAL_SET_PATH}", file=sys.stderr)
        return 2

    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    if args.limit:
        eval_set = {
            "version": eval_set.get("version"),
            "in_corpus": eval_set["in_corpus"][: args.limit],
            "out_of_corpus": eval_set["out_of_corpus"][: max(1, args.limit // 5)],
        }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.ablate:
        sweeps = []
        for top_k in (3, 5, 8):
            for chunk_size in (700, 1100, 1500):
                for rerank in (False, True):
                    cfg = RunConfig(
                        top_k=top_k, chunk_size=chunk_size, use_reranker=rerank
                    )
                    print(f"== ablation: {cfg} ==")
                    run = run_once(
                        eval_set,
                        sleep_s=args.sleep,
                        cfg=cfg,
                        rebuild_for_chunk_size=True,
                    )
                    sweeps.append(run)
        write_ablations_md(sweeps, RESULTS_DIR / "ablations.md")
        (RESULTS_DIR / "ablations.json").write_text(
            json.dumps(sweeps, indent=2), encoding="utf-8"
        )
        print(f"Wrote {RESULTS_DIR/'ablations.md'} and ablations.json")
        return 0

    print(f"Running eval against {GROQ_MODEL} (sleep={args.sleep}s between calls)…")
    started = time.time()
    run = run_once(eval_set, sleep_s=args.sleep)
    elapsed = time.time() - started
    print(f"Done in {elapsed:.1f}s.")

    out_json = RESULTS_DIR / "eval_results.json"
    out_md = RESULTS_DIR / "summary.md"
    out_json.write_text(json.dumps(run, indent=2), encoding="utf-8")
    write_summary_md(run["summary"], out_md)
    print(f"Wrote {out_json} and {out_md}.")
    print(json.dumps(run["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
