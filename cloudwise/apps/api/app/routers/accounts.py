from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import AWSAccount, User
from ..schemas import AWSAccountCreate, AWSAccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=List[AWSAccountOut])
def list_accounts(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> List[AWSAccount]:
    # The org_id filter here is defense in depth, not the safety mechanism —
    # RLS (see db/init.sql) would refuse cross-org rows even without it.
    return list(db.execute(select(AWSAccount).where(AWSAccount.org_id == user.org_id)).scalars())


@router.post("", response_model=AWSAccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AWSAccountCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> AWSAccount:
    account = AWSAccount(org_id=user.org_id, **payload.model_dump())
    db.add(account)
    db.flush()
    db.refresh(account)
    return account
