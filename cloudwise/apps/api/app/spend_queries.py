"""Shared spend-aggregation query, used by both the /spend HTTP route and the
AI copilot's get_spend tool (services/copilot/tools.py) — one place computes
this number, so the dashboard and the copilot's answers can never disagree.
"""
from datetime import date, timedelta
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import SpendDaily

GroupBy = Literal["service", "account", "day"]
View = Literal["unblended", "amortized"]


def get_spend_summary(
    db: Session,
    org_id: UUID,
    group_by: GroupBy = "service",
    view: View = "unblended",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=30))

    cost_column = SpendDaily.amortized_cost if view == "amortized" else SpendDaily.unblended_cost
    group_column = {
        "service": SpendDaily.service,
        "account": SpendDaily.account_id,
        "day": SpendDaily.usage_date,
    }[group_by]

    rows = db.execute(
        select(group_column, func.sum(cost_column))
        .where(SpendDaily.org_id == org_id, SpendDaily.usage_date.between(start_date, end_date))
        .group_by(group_column)
        .order_by(func.sum(cost_column).desc())
    ).all()

    breakdown = [{"key": str(key), "cost": round(float(cost), 2)} for key, cost in rows]
    return {
        "start_date": start_date,
        "end_date": end_date,
        "view": view,
        "group_by": group_by,
        "currency": "USD",
        "total_cost": round(sum(b["cost"] for b in breakdown), 2),
        "breakdown": breakdown,
    }
