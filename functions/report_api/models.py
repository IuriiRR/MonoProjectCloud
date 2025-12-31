from __future__ import annotations

from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field

Number = Union[int, float]


class ReportTransaction(BaseModel):
    id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)

    time: int
    description: Optional[str] = None
    amount: Number
    balance: Optional[Number] = None
    currency: Optional[Dict[str, Any]] = None

    # Enriched from accounts lookup
    account_type: Optional[Literal["jar", "card"]] = None
    account_title: Optional[str] = None


class DailyReportRequest(BaseModel):
    # YYYY-MM-DD; defaults to "today" in report timezone when omitted.
    date: Optional[str] = None


class CoverageSource(BaseModel):
    tx_id: str = Field(min_length=1)
    amount_cents: int


class SpendCoverage(BaseModel):
    tx_id: str = Field(min_length=1)
    covered: bool
    covered_cents: int = 0
    uncovered_cents: int = 0
    sources: list[CoverageSource] = []
    reason: Optional[str] = None


class DailyReportResponse(BaseModel):
    user_id: str
    date: str
    timezone: str
    totals: Dict[str, int]  # cents: spend_total (abs), earn_total, net
    spends: list[SpendCoverage]
    report_markdown: str
    # Optional, provided if LLM is enabled
    report_html: Optional[str] = None

