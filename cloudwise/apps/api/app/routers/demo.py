"""Public, read-only endpoints over the synthetic 'Acme Demo' org (see
demo/seed_demo.py) — no Clerk auth at all, deliberately, so a LinkedIn
visitor can browse the dashboard without connecting a real AWS account or
even signing up. No write endpoints exist here on purpose; the frontend's
demo mode should show what a write button *would* do rather than call one.

Not yet built: the copilot in demo mode (blueprint wants a per-session
message cap and a daily global LLM budget on it, which needs actual rate
limiting infrastructure — skipped for now rather than shipped unbounded).
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ..database import SessionLocal, org_scoped_session
from ..models import AWSAccount, Finding, Organization
from ..schemas import AWSAccountOut, FindingOut, SpendSummary
from ..spend_queries import GroupBy, View, get_spend_summary

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_CLERK_ORG_ID = "demo_org_fixed"


def _get_demo_org_id():
    session = SessionLocal()
    try:
        org = session.execute(
            select(Organization).where(Organization.clerk_org_id == DEMO_CLERK_ORG_ID)
        ).scalar_one_or_none()
        if org is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Demo org not seeded yet; run demo/seed_demo.py"
            )
        return org.id
    finally:
        session.close()


@router.get("/accounts", response_model=List[AWSAccountOut])
def demo_accounts() -> List[AWSAccount]:
    org_id = _get_demo_org_id()
    with org_scoped_session(org_id=str(org_id)) as session:
        return list(session.execute(select(AWSAccount).where(AWSAccount.org_id == org_id)).scalars())


@router.get("/findings", response_model=List[FindingOut])
def demo_findings() -> List[Finding]:
    org_id = _get_demo_org_id()
    with org_scoped_session(org_id=str(org_id)) as session:
        return list(session.execute(select(Finding).where(Finding.org_id == org_id)).scalars())


@router.get("/spend", response_model=SpendSummary)
def demo_spend(
    group_by: GroupBy = "service",
    view: View = "unblended",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> SpendSummary:
    org_id = _get_demo_org_id()
    with org_scoped_session(org_id=str(org_id)) as session:
        return SpendSummary(**get_spend_summary(session, org_id, group_by, view, start_date, end_date))
