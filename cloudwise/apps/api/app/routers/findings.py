from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Finding, User
from ..schemas import FindingOut

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=List[FindingOut])
def list_findings(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> List[Finding]:
    return list(db.execute(select(Finding).where(Finding.org_id == user.org_id)).scalars())
