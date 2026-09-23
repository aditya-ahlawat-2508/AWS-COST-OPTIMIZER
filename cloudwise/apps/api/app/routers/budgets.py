import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Budget, SpendDaily, User
from ..schemas import BudgetCreate, BudgetOut

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _month_to_date_spend(db: Session, org_id, account_id: Optional[str]) -> float:
    today = datetime.date.today()
    start_of_month = today.replace(day=1)

    query = select(func.coalesce(func.sum(SpendDaily.unblended_cost), 0)).where(
        SpendDaily.org_id == org_id, SpendDaily.usage_date >= start_of_month
    )
    if account_id is not None:
        query = query.where(SpendDaily.account_id == account_id)

    return round(float(db.execute(query).scalar_one()), 2)


@router.get("", response_model=List[BudgetOut])
def list_budgets(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> List[BudgetOut]:
    budgets = db.execute(select(Budget).where(Budget.org_id == user.org_id)).scalars().all()
    return [
        BudgetOut(
            id=b.id,
            account_id=b.account_id,
            name=b.name,
            monthly_limit_usd=float(b.monthly_limit_usd),
            spent_this_month=_month_to_date_spend(db, user.org_id, str(b.account_id) if b.account_id else None),
        )
        for b in budgets
    ]


@router.post("", response_model=BudgetOut, status_code=201)
def create_budget(
    payload: BudgetCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> BudgetOut:
    budget = Budget(org_id=user.org_id, **payload.model_dump())
    db.add(budget)
    db.flush()
    db.refresh(budget)
    return BudgetOut(
        id=budget.id,
        account_id=budget.account_id,
        name=budget.name,
        monthly_limit_usd=float(budget.monthly_limit_usd),
        spent_this_month=_month_to_date_spend(db, user.org_id, str(budget.account_id) if budget.account_id else None),
    )
