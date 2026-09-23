"""Gathers one org's real data and sends its weekly Slack digest. Cross-package
coupling with apps/api's models, same as services/cur/loader.py.
"""
from datetime import date, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .slack import format_weekly_digest, send_slack_message


def send_weekly_digest_for_org(
    db: Session, org_id: UUID, org_name: str, webhook_url: str, http_client: Optional[Any] = None
) -> bool:
    from sqlalchemy import select

    from app.models import Finding
    from app.spend_queries import get_spend_summary

    spend = get_spend_summary(
        db, org_id, group_by="service", view="unblended",
        start_date=date.today() - timedelta(days=30), end_date=date.today(),
    )

    open_findings = db.execute(
        select(Finding).where(Finding.org_id == org_id, Finding.status == "open")
    ).scalars().all()
    open_savings_total = sum(float(f.monthly_savings) for f in open_findings)
    top_findings = sorted(
        (
            {
                "resource_id": f.resource_id,
                "monthly_savings": float(f.monthly_savings),
                "effort": f.effort,
                "risk": f.risk,
            }
            for f in open_findings
        ),
        key=lambda f: f["monthly_savings"],
        reverse=True,
    )

    realized_total = sum(
        float(f.monthly_savings)
        for f in db.execute(select(Finding).where(Finding.org_id == org_id, Finding.status == "done")).scalars()
    )

    text = format_weekly_digest(
        org_name=org_name,
        total_spend=spend["total_cost"],
        open_findings_count=len(open_findings),
        open_savings_total=open_savings_total,
        top_findings=top_findings,
        realized_savings_this_period=realized_total,
    )

    if http_client is not None:
        return send_slack_message(webhook_url, text, http_client=http_client)
    return send_slack_message(webhook_url, text)
