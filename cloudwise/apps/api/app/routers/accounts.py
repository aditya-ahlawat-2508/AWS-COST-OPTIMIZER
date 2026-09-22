import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import billing
from ..deps import get_current_user, get_db
from ..models import AWSAccount, User
from ..schemas import AWSAccountCreate, AWSAccountOut, ScanResult

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
    entitlement = billing.get_entitlement(db, user.org_id)
    max_accounts = entitlement["max_accounts"]
    if max_accounts is not None:
        current_count = len(db.execute(select(AWSAccount).where(AWSAccount.org_id == user.org_id)).all())
        if current_count >= max_accounts:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Your {entitlement['tier']} plan allows up to {max_accounts} connected AWS account(s). "
                    "Upgrade to connect more."
                ),
            )

    account = AWSAccount(org_id=user.org_id, **payload.model_dump())
    db.add(account)
    db.flush()
    db.refresh(account)
    return account


@router.post("/{account_id}/scan", response_model=ScanResult)
def scan_account(
    account_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ScanResult:
    # services.scanner is a sibling package to apps/api — see
    # services/cur/loader.py's docstring for why this monorepo runs with both
    # on PYTHONPATH. Imported here (not at module load) so importing this
    # router never requires boto3/AWS creds to be configured.
    from services.scanner.orchestrator import run_scan_for_account

    account = db.get(AWSAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AWS account not found")

    try:
        result = run_scan_for_account(db, user.org_id, account)
    except Exception as exc:
        account.status = "error"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Scan failed: {exc}")

    account.status = "connected"
    account.last_scanned_at = datetime.utcnow()
    return ScanResult(**result)
