from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from .matching import SpendMatch, Tx


def _fmt_money(cents: int) -> str:
    return f"{cents / 100:.2f} UAH"


def _fmt_time(ts: int, tz: timezone) -> str:
    return datetime.fromtimestamp(ts, tz=tz).strftime("%H:%M")


def render_markdown_report(
    *,
    date: str,
    tz_name: str,
    tzinfo: timezone,
    txs: List[Tx],
    matches: List[SpendMatch],
    accounts_by_id: Dict[str, Dict],
    uncovered_reason: Optional[str] = None,
) -> str:
    spends = [t for t in txs if t.amount_cents < 0]
    earns = [t for t in txs if t.amount_cents > 0]

    spend_total = sum(-t.amount_cents for t in spends)
    earn_total = sum(t.amount_cents for t in earns)
    net = earn_total - spend_total

    lines: List[str] = []
    lines.append(f"## Daily transactions report — {date} ({tz_name})")
    lines.append("")
    lines.append(f"- **Total spends**: {_fmt_money(spend_total)}")
    lines.append(f"- **Total earnings**: {_fmt_money(earn_total)}")
    lines.append(f"- **Net**: {_fmt_money(net)}")
    lines.append("")

    # Covered / Uncovered spends
    covered = [m for m in matches if m.covered]
    uncovered = [m for m in matches if not m.covered]

    lines.append(f"### Spends ({len(matches)})")
    lines.append("")
    for m in matches:
        spend_tx = next((t for t in spends if t.id == m.spend_tx_id), None)
        if not spend_tx:
            continue
        icon = "✅" if m.covered else "❌"
        label = spend_tx.description or "(no description)"
        lines.append(
            f"- {icon} **{_fmt_money(m.spend_abs_cents)}** — {label} ({_fmt_time(spend_tx.time, tzinfo)})"
        )
        if m.sources:
            src_parts = []
            for src_id, amt in m.sources:
                earn_tx = next((t for t in earns if t.id == src_id), None)
                src_label = (earn_tx.description if earn_tx else None) or src_id
                src_parts.append(f"{_fmt_money(amt)} from `{src_id}` ({src_label})")
            lines.append(f"  - Covered by: " + "; ".join(src_parts))
        if not m.covered:
            lines.append(f"  - Uncovered: **{_fmt_money(m.uncovered_cents)}**")
            if uncovered_reason:
                lines.append(f"  - Note: {uncovered_reason}")

    lines.append("")
    lines.append(f"### Earnings ({len(earns)})")
    lines.append("")
    for e in sorted(earns, key=lambda x: x.time):
        label = e.description or "(no description)"
        lines.append(f"- 💰 **{_fmt_money(e.amount_cents)}** — {label} ({_fmt_time(e.time, tzinfo)})")

    lines.append("")
    lines.append("### Notes")
    lines.append("")
    lines.append(
        "- Coverage is computed across **all accounts** (cards + jars) for the selected day, based on matching earnings to spends."
    )
    lines.append(
        "- This is a heuristic: transfers, holds, refunds, and multi-currency behavior may require extra logic later."
    )
    lines.append("")
    return "\n".join(lines)

