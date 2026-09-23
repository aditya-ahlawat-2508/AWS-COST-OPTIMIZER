from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import AuditLog, User
from ..schemas import AuditLogOut

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=List[AuditLogOut])
def list_audit_log(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> List[AuditLog]:
    return list(
        db.execute(
            select(AuditLog).where(AuditLog.org_id == user.org_id).order_by(AuditLog.created_at.desc())
        ).scalars()
    )
