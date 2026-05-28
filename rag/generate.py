"""Build the prompt, call Groq, parse citations, enforce guardrails."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from rag.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    MAX_OUTPUT_TOKENS,
    REFUSAL_MESSAGE,
    SCORE_THRESHOLD,
)


SYSTEM_PROMPT = """You are Zidipay's internal policy assistant.

You answer employee questions about Zidipay's policies and procedures using ONLY the context blocks provided.

Rules you must follow:
1. Answer ONLY from the provided context. Do not use any outside knowledge.
2. Every factual claim in your answer MUST cite the supporting context block, using bracketed labels like [1], [2], etc. — these are the numbers shown on each context block.
3. Be concise. Use plain English, short paragraphs, and bullet points where appropriate.
4. If the context does not contain enough information to answer the question, reply with EXACTLY this sentence and nothing else:
   "I can only answer questions about Zidipay's policies and procedures."
5. Never invent document titles, sections, numbers, dates, or policy details that are not in the context.
6. If the question asks about something outside Zidipay's policies (general knowledge, opinions, other companies, current events), reply with EXACTLY the refusal sentence in rule 4.
"""


@dataclass
class Citation:
    doc_id: str
    doc_title: str
    section: str
    source: str
    snippet: str
    chunk_id: str = ""


def _truncate(text: str, max_chars: int = 320) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _format_context(chunks: list[Document]) -> str:
    """Number each chunk and label it 'doc_title — section'."""
    lines = []
    for i, doc in enumerate(chunks, start=1):
        title = doc.metadata.get("doc_title", "Untitled")
        section = doc.metadata.get("section", "")
        label = title if not section else f"{title} — {section}"
        lines.append(f"[{i}] {label}\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(lines)


def _extract_used_indices(answer: str, total: int) -> list[int]:
    """Find which [n] tags the answer cites, returning 1-based indices that are in range."""
    found = re.findall(r"\[(\d+)\]", answer or "")
    seen: set[int] = set()
    used: list[int] = []
    for s in found:
        try:
            n = int(s)
        except ValueError:
            continue
        if 1 <= n <= total and n not in seen:
            seen.add(n)
            used.append(n)
    return used


def _build_citations(
    chunks: list[Document], used_idx: list[int]
) -> list[Citation]:
    """Turn used indices into structured Citation objects. If none, default to all chunks."""
    indices = used_idx or list(range(1, len(chunks) + 1))
    citations: list[Citation] = []
    seen_keys: set[tuple[str, str]] = set()
    for i in indices:
        if i < 1 or i > len(chunks):
            continue
        doc = chunks[i - 1]
        meta = doc.metadata or {}
        key = (meta.get("doc_id", ""), meta.get("section", ""))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        citations.append(
            Citation(
                doc_id=meta.get("doc_id", ""),
                doc_title=meta.get("doc_title", "Untitled"),
                section=meta.get("section", ""),
                source=meta.get("source", ""),
                snippet=_truncate(doc.page_content),
                chunk_id=meta.get("chunk_id", ""),
            )
        )
    return citations


def _make_llm(model: Optional[str] = None, max_tokens: Optional[int] = None) -> ChatGroq:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to .env or your environment."
        )
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=model or GROQ_MODEL,
        temperature=0,
        max_tokens=max_tokens or MAX_OUTPUT_TOKENS,
    )


def _refusal_payload() -> dict:
    return {"answer": REFUSAL_MESSAGE, "citations": [], "refused": True}


def generate_answer(
    question: str,
    results: list[tuple[Document, float]],
    score_threshold: Optional[float] = None,
    llm: Optional[ChatGroq] = None,
) -> dict:
    """Build the prompt → call Groq → parse citations → enforce guardrails.

    Returns: {"answer": str, "citations": list[Citation], "refused": bool}
    """
    threshold = SCORE_THRESHOLD if score_threshold is None else score_threshold

    if not results:
        return _refusal_payload()

    best = results[0][1] if results else 0.0
    if best < threshold:
        return _refusal_payload()

    chunks = [doc for doc, _ in results]
    context = _format_context(chunks)
    user_msg = (
        f"Question: {question}\n\n"
        f"Context (numbered blocks):\n\n{context}\n\n"
        "Answer concisely. Cite the supporting context block(s) using [n]."
    )

    chat = llm or _make_llm()
    response = chat.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_msg)]
    )
    raw = (response.content or "").strip()

    # Did the model emit the refusal? Treat as refusal even if it added stray text.
    if raw.lower().startswith(REFUSAL_MESSAGE.lower().rstrip(".")):
        return _refusal_payload()

    used = _extract_used_indices(raw, len(chunks))
    citations = _build_citations(chunks, used)
    return {"answer": raw, "citations": citations, "refused": False}
