from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import SpendSummary
from ..spend_queries import GroupBy, View, get_spend_summary

router = APIRouter(prefix="/spend", tags=["spend"])


@router.get("", response_model=SpendSummary)
def get_spend(
    group_by: GroupBy = "service",
    view: View = "unblended",
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SpendSummary:
    return SpendSummary(**get_spend_summary(db, user.org_id, group_by, view, start_date, end_date))
