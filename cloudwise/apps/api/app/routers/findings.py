import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Finding, User
from ..schemas import FindingOut

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=List[FindingOut])
def list_findings(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> List[Finding]:
    return list(db.execute(select(Finding).where(Finding.org_id == user.org_id)).scalars())


@router.get("/{finding_id}", response_model=FindingOut)
def get_finding(
    finding_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Finding:
    # RLS (db/init.sql) already guarantees db.get() can't return a row from
    # another org; the 404 here is just the right HTTP response for that case.
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return finding
