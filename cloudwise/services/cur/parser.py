"""Parses AWS Cost and Usage Report (CUR 2.0 / Data Exports) line items into
normalized daily-by-service spend records.

Deliberate simplification, stated plainly rather than hidden: real CUR
amortization nets out recurring RI/Savings Plan fee lines against the
upfront-fee amortization columns to avoid double-counting, which needs the
full reservation/SP line-item detail. This implementation approximates
amortized cost as unblended cost plus the two amortization columns CUR
already provides per line item — directionally correct (it's what makes
amortized > unblended for RI/SP-covered usage, and roughly right in size),
but not a full CUR amortization engine. Good enough for the dashboard's
"amortized vs unblended" toggle; revisit before this number appears on an
invoice.

Line items with line_item_line_item_type in EXCLUDED_LINE_ITEM_TYPES are
left out of both figures, per the blueprint's fix for Cost Explorer's
"UnblendedCost includes credits/refunds noise" problem — the same fix
applies here since it's the same underlying billing data.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List

EXCLUDED_LINE_ITEM_TYPES = {"Credit", "Refund", "Tax"}


@dataclass(frozen=True)
class DailyServiceSpend:
    usage_account_id: str
    usage_date: date
    service: str
    unblended_cost: float
    amortized_cost: float
    currency: str


def parse_cur_rows(rows: Iterable[Dict[str, Any]]) -> List[DailyServiceSpend]:
    """rows: dicts keyed by CUR 2.0's column names, as read from its CSV/Parquet
    export (e.g. via csv.DictReader) — this function does no file I/O itself.

    Expected keys per row: line_item_usage_account_id, line_item_usage_start_date
    (an ISO date/datetime string), line_item_product_code, line_item_line_item_type,
    line_item_unblended_cost, line_item_currency_code, and optionally
    reservation_amortized_upfront_fee_for_billing_period /
    savings_plan_amortized_upfront_commitment_for_billing_period.
    """
    totals: Dict[tuple, Dict[str, float]] = defaultdict(lambda: {"unblended": 0.0, "amortized": 0.0})
    currency_by_key: Dict[tuple, str] = {}

    for row in rows:
        line_item_type = row.get("line_item_line_item_type", "Usage")
        if line_item_type in EXCLUDED_LINE_ITEM_TYPES:
            continue

        usage_account_id = row["line_item_usage_account_id"]
        usage_date = _parse_date(row["line_item_usage_start_date"])
        service = row["line_item_product_code"]
        unblended = float(row.get("line_item_unblended_cost", 0) or 0)
        ri_amortization = float(row.get("reservation_amortized_upfront_fee_for_billing_period", 0) or 0)
        sp_amortization = float(row.get("savings_plan_amortized_upfront_commitment_for_billing_period", 0) or 0)

        key = (usage_account_id, usage_date, service)
        totals[key]["unblended"] += unblended
        totals[key]["amortized"] += unblended + ri_amortization + sp_amortization
        currency_by_key[key] = row.get("line_item_currency_code", "USD")

    return [
        DailyServiceSpend(
            usage_account_id=account_id,
            usage_date=usage_date,
            service=service,
            unblended_cost=round(values["unblended"], 4),
            amortized_cost=round(values["amortized"], 4),
            currency=currency_by_key[(account_id, usage_date, service)],
        )
        for (account_id, usage_date, service), values in totals.items()
    ]


def _parse_date(value: str) -> date:
    # CUR timestamps look like "2026-09-01T00:00:00Z" or "2026-09-01 00:00:00".
    return date.fromisoformat(value[:10])
