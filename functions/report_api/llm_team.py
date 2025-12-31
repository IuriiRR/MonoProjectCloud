from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, List, Optional, Tuple

from .matching import SpendMatch, Tx


@dataclass
class LlmReportResult:
    report_markdown: str
    report_html: Optional[str] = None
    # Optionally: a refined spends coverage mapping
    refined_matches: Optional[List[SpendMatch]] = None


def _llm_available() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _safe_json_loads(s: str) -> Any:
    try:
        return json.loads(s)
    except Exception:
        return None


# In-process limiter to reduce 429s (cannot coordinate across multiple Cloud Run instances).
# Default: 5 requests per 60s.
_LLM_CALL_TIMES = deque()  # type: ignore[var-annotated]


def _rate_limit_ok(*, limit: int = 5, window_s: int = 60) -> bool:
    now = time.time()
    while _LLM_CALL_TIMES and now - _LLM_CALL_TIMES[0] > window_s:
        _LLM_CALL_TIMES.popleft()
    if len(_LLM_CALL_TIMES) >= limit:
        return False
    _LLM_CALL_TIMES.append(now)
    return True


def _validate_reconcile_payload(
    payload: Any,
    *,
    spends_by_id: Dict[str, int],
    earns_by_id: Dict[str, int],
) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not isinstance(payload, dict):
        return False, ["Payload is not a JSON object"]

    spends = payload.get("spends")
    if not isinstance(spends, list):
        return False, ["Missing/invalid 'spends' list"]

    earn_used: Dict[str, int] = {}
    for i, item in enumerate(spends):
        if not isinstance(item, dict):
            errors.append(f"spends[{i}] is not an object")
            continue
        tx_id = item.get("tx_id")
        if not isinstance(tx_id, str) or not tx_id:
            errors.append(f"spends[{i}].tx_id missing/invalid")
            continue
        if tx_id not in spends_by_id:
            errors.append(f"spends[{i}].tx_id '{tx_id}' is not a spend transaction id")
            continue
        sources = item.get("sources", [])
        if sources is None:
            sources = []
        if not isinstance(sources, list):
            errors.append(f"spends[{i}].sources must be a list")
            continue
        total = 0
        for j, src in enumerate(sources):
            if not isinstance(src, dict):
                errors.append(f"spends[{i}].sources[{j}] is not an object")
                continue
            sid = src.get("tx_id")
            amt = src.get("amount_cents")
            if not isinstance(sid, str) or not sid:
                errors.append(f"spends[{i}].sources[{j}].tx_id missing/invalid")
                continue
            if sid not in earns_by_id:
                errors.append(f"spends[{i}].sources[{j}].tx_id '{sid}' is not an earning tx id")
                continue
            if not isinstance(amt, int) or amt <= 0:
                errors.append(f"spends[{i}].sources[{j}].amount_cents must be positive int")
                continue
            earn_used[sid] = earn_used.get(sid, 0) + amt
            total += amt
        if total > spends_by_id[tx_id]:
            errors.append(f"spend '{tx_id}' over-covered: {total} > {spends_by_id[tx_id]}")

    for sid, used in earn_used.items():
        if used > earns_by_id[sid]:
            errors.append(f"earning '{sid}' over-used: {used} > {earns_by_id[sid]}")

    return (len(errors) == 0), errors


def maybe_refine_and_write_report_with_llm(
    *,
    txs: List[Tx],
    initial_matches: List[SpendMatch],
    fallback_markdown: str,
    model: str = "models/gemini-2.5-flash-lite",
    temperature: float = 0.0,
    max_iters: int = 1,
) -> LlmReportResult:
    """
    If GEMINI_API_KEY is set and LangChain deps are available, run a small agent loop:
      - Reconciler proposes coverage JSON (can adjust initial matches)
      - Critic validates (we also validate in code)
      - Iterate up to max_iters
      - Writer produces report markdown + html

    If unavailable, return fallback_markdown.
    """
    if not _llm_available():
        return LlmReportResult(report_markdown=fallback_markdown, report_html=None, refined_matches=None)

    # Avoid hammering strict RPM limits: if we're already at the cap, just return fallback.
    if not _rate_limit_ok():
        return LlmReportResult(report_markdown=fallback_markdown, report_html=None, refined_matches=initial_matches)

    try:  # pragma: no cover
        from google import genai  # type: ignore[import-not-found]
    except Exception:
        return LlmReportResult(report_markdown=fallback_markdown, report_html=None, refined_matches=None)

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return LlmReportResult(report_markdown=fallback_markdown, report_html=None, refined_matches=None)

    client = genai.Client(api_key=api_key)

    spends = [t for t in txs if t.amount_cents < 0]
    earns = [t for t in txs if t.amount_cents > 0]
    spends_by_id = {t.id: -t.amount_cents for t in spends}
    earns_by_id = {t.id: t.amount_cents for t in earns}

    tx_payload = [
        {
            "id": t.id,
            "time": t.time,
            "amount_cents": t.amount_cents,
            "description": t.description,
        }
        for t in txs
    ]

    # Seed suggestion from deterministic matcher (gives the model a strong starting point).
    suggestion = {
        "spends": [
            {
                "tx_id": m.spend_tx_id,
                "sources": [{"tx_id": sid, "amount_cents": amt} for (sid, amt) in m.sources],
            }
            for m in initial_matches
        ]
    }

    # Single-call strategy to fit strict RPM limits:
    # Ask for BOTH reconciliation + report in one JSON response. If invalid, fall back (no retries).
    prompt = {
        "task": "reconcile_and_write_daily_report",
        "rules": [
            "SPEND has negative amount_cents; EARNING has positive amount_cents.",
            "Do not invent transactions. Use only provided ids.",
            "Never allocate more than available in an earning.",
            "Never allocate more than spend absolute amount.",
            "Return STRICT JSON only (no markdown fences).",
        ],
        "output_schema": {
            "reconcile": {"spends": [{"tx_id": "string", "sources": [{"tx_id": "string", "amount_cents": 123}]}]},
            "report_markdown": "string",
            "report_html": "string (optional, can be null)",
        },
        "transactions": tx_payload,
        "suggested_reconcile": suggestion,
        "fallback_markdown": fallback_markdown,
        "style": {
            "icons": {"covered": "✅", "uncovered": "❌", "earning": "💰"},
            "html": "minimal, no scripts, no external resources",
        },
        "temperature": temperature,
    }

    # Cache key for LLM output (best-effort, in-process)
    tx_hash = sha256(json.dumps(tx_payload, sort_keys=True).encode("utf-8")).hexdigest()
    cache_key = f"{model}:{tx_hash}"
    inproc_cache: Dict[str, LlmReportResult] = getattr(maybe_refine_and_write_report_with_llm, "_cache", {})
    if cache_key in inproc_cache:
        return inproc_cache[cache_key]

    try:
        resp = client.chats.create(model=model).send_message(json.dumps(prompt, ensure_ascii=False))
        raw = getattr(resp, "text", None) or ""
    except Exception:
        return LlmReportResult(report_markdown=fallback_markdown, report_html=None, refined_matches=initial_matches)

    payload = _safe_json_loads(raw)
    if not isinstance(payload, dict):
        return LlmReportResult(report_markdown=fallback_markdown, report_html=None, refined_matches=initial_matches)

    reconcile = payload.get("reconcile")
    if not isinstance(reconcile, dict):
        return LlmReportResult(report_markdown=fallback_markdown, report_html=None, refined_matches=initial_matches)

    ok, errors = _validate_reconcile_payload(reconcile, spends_by_id=spends_by_id, earns_by_id=earns_by_id)
    if not ok:
        # Strict: don't retry (saves RPM); fall back.
        return LlmReportResult(report_markdown=fallback_markdown, report_html=None, refined_matches=initial_matches)

    refined: List[SpendMatch] = []
    spends_list = reconcile.get("spends")
    if isinstance(spends_list, list):
        for item in spends_list:
            if not isinstance(item, dict):
                continue
            sid = item.get("tx_id")
            if not isinstance(sid, str) or sid not in spends_by_id:
                continue
            srcs = item.get("sources") or []
            sources_list: List[Tuple[str, int]] = []
            if isinstance(srcs, list):
                for s in srcs:
                    if not isinstance(s, dict):
                        continue
                    tid = s.get("tx_id")
                    amt = s.get("amount_cents")
                    if isinstance(tid, str) and isinstance(amt, int) and amt > 0:
                        sources_list.append((tid, amt))
            refined.append(SpendMatch(spend_tx_id=sid, spend_abs_cents=spends_by_id[sid], sources=sources_list))
    if not refined:
        refined = initial_matches

    report_md = payload.get("report_markdown")
    if not isinstance(report_md, str) or not report_md.strip():
        report_md = fallback_markdown
    report_html = payload.get("report_html")
    if report_html is not None and not isinstance(report_html, str):
        report_html = None

    result = LlmReportResult(report_markdown=report_md, report_html=report_html, refined_matches=refined)
    inproc_cache[cache_key] = result
    setattr(maybe_refine_and_write_report_with_llm, "_cache", inproc_cache)
    return result

