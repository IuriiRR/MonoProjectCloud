from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Tx:
    id: str
    time: int
    amount_cents: int  # positive for earnings, negative for spends
    description: str = ""


@dataclass
class SpendMatch:
    spend_tx_id: str
    spend_abs_cents: int
    sources: List[Tuple[str, int]]  # (earn_tx_id, allocated_cents)

    @property
    def covered_cents(self) -> int:
        return sum(a for _tid, a in self.sources)

    @property
    def uncovered_cents(self) -> int:
        return max(0, self.spend_abs_cents - self.covered_cents)

    @property
    def covered(self) -> bool:
        return self.uncovered_cents == 0


def _subset_sum_indices(values: List[int], target: int, max_items: int) -> List[int] | None:
    """
    Return indices of a subset of `values` that sums to target.
    Backtracking with pruning; intended for small N (daily tx volume).
    """
    indexed = list(enumerate(values))
    indexed.sort(key=lambda x: x[1], reverse=True)

    best: List[int] | None = None

    def rec(i: int, remaining: int, chosen: List[int]) -> None:
        nonlocal best
        if remaining == 0:
            best = list(chosen)
            return
        if remaining < 0:
            return
        if i >= len(indexed):
            return
        if best is not None:
            return
        if len(chosen) >= max_items:
            return

        idx, val = indexed[i]
        # Choose
        chosen.append(idx)
        rec(i + 1, remaining - val, chosen)
        chosen.pop()
        # Skip
        rec(i + 1, remaining, chosen)

    rec(0, target, [])
    return best


def match_spends_to_earnings(
    transactions: List[Tx],
    *,
    max_subset_items: int = 6,
) -> Tuple[List[SpendMatch], Dict[str, int]]:
    """
    Heuristic multi-pass matcher:
    - Exact amount 1:1
    - Many-to-one (subset of spends equals one earning)
    - One-to-many (subset of earnings equals one spend)
    - Greedy allocation of remaining earnings to remaining spends

    Returns:
      - matches per spend transaction (one entry per spend, covered or not)
      - remaining earnings per earning tx id (cents) after allocations
    """
    spends = [t for t in transactions if t.amount_cents < 0]
    earns = [t for t in transactions if t.amount_cents > 0]

    spend_abs: Dict[str, int] = {s.id: -s.amount_cents for s in spends}
    earn_remaining: Dict[str, int] = {e.id: e.amount_cents for e in earns}
    spend_remaining: Dict[str, int] = dict(spend_abs)

    allocations: Dict[str, List[Tuple[str, int]]] = {s.id: [] for s in spends}

    # Pass 1: exact matches 1:1 (prefer closest in time)
    earns_by_amt: Dict[int, List[Tx]] = {}
    for e in earns:
        earns_by_amt.setdefault(e.amount_cents, []).append(e)
    for amt, lst in earns_by_amt.items():
        lst.sort(key=lambda x: x.time)

    for s in sorted(spends, key=lambda x: x.time):
        amt = spend_remaining.get(s.id, 0)
        if amt <= 0:
            continue
        candidates = earns_by_amt.get(amt, [])
        # find first candidate with remaining
        chosen = next((e for e in candidates if earn_remaining.get(e.id, 0) >= amt), None)
        if not chosen:
            continue
        allocations[s.id].append((chosen.id, amt))
        spend_remaining[s.id] = 0
        earn_remaining[chosen.id] -= amt

    # Helper lists of unmatched
    def unmatched_spends() -> List[Tx]:
        return [s for s in spends if spend_remaining.get(s.id, 0) > 0]

    def unmatched_earns() -> List[Tx]:
        return [e for e in earns if earn_remaining.get(e.id, 0) > 0]

    # Pass 2: many-to-one: subset of spends equals one earning
    # Iterate earnings largest first to reduce search.
    for e in sorted(unmatched_earns(), key=lambda x: x.amount_cents, reverse=True):
        target = earn_remaining[e.id]
        if target <= 0:
            continue
        s_list = unmatched_spends()
        vals = [spend_remaining[s.id] for s in s_list]
        idxs = _subset_sum_indices(vals, target, max_subset_items)
        if not idxs:
            continue
        for i in idxs:
            s = s_list[i]
            amt = spend_remaining[s.id]
            if amt <= 0:
                continue
            allocations[s.id].append((e.id, amt))
            spend_remaining[s.id] = 0
            earn_remaining[e.id] -= amt

    # Pass 3: one-to-many: subset of earnings equals one spend
    for s in sorted(unmatched_spends(), key=lambda x: spend_remaining[s.id], reverse=True):
        target = spend_remaining[s.id]
        e_list = unmatched_earns()
        vals = [earn_remaining[e.id] for e in e_list]
        idxs = _subset_sum_indices(vals, target, max_subset_items)
        if not idxs:
            continue
        for i in idxs:
            e = e_list[i]
            amt = earn_remaining[e.id]
            if amt <= 0:
                continue
            allocations[s.id].append((e.id, amt))
            spend_remaining[s.id] -= amt
            earn_remaining[e.id] = 0

    # Pass 4: greedy allocation of remaining earnings to remaining spends.
    # Heuristic: cover as many spends as possible => allocate smaller spends first,
    # using largest remaining earnings as sources.
    remaining_spends_sorted = sorted(unmatched_spends(), key=lambda x: spend_remaining[x.id])
    remaining_earns_sorted = sorted(unmatched_earns(), key=lambda x: earn_remaining[x.id], reverse=True)

    e_idx = 0
    for s in remaining_spends_sorted:
        need = spend_remaining[s.id]
        if need <= 0:
            continue
        while need > 0 and e_idx < len(remaining_earns_sorted):
            e = remaining_earns_sorted[e_idx]
            avail = earn_remaining[e.id]
            if avail <= 0:
                e_idx += 1
                continue
            take = min(need, avail)
            allocations[s.id].append((e.id, take))
            earn_remaining[e.id] -= take
            need -= take
        spend_remaining[s.id] = need

    matches: List[SpendMatch] = []
    for s in sorted(spends, key=lambda x: x.time):
        sources = allocations.get(s.id, [])
        matches.append(SpendMatch(spend_tx_id=s.id, spend_abs_cents=spend_abs[s.id], sources=sources))

    return matches, earn_remaining

