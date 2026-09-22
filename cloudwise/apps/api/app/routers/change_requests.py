import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import AWSAccount, ChangeRequest, Finding, User
from ..schemas import ChangeRequestOut

router = APIRouter(prefix="/change-requests", tags=["change-requests"])

# Approving a change (as opposed to just proposing one, which the copilot or
# any viewer can do) is the point at which something will actually happen to
# a customer's AWS account, so it's gated to roles above "viewer".
APPROVER_ROLES = {"owner", "admin", "approver"}


@router.get("", response_model=List[ChangeRequestOut])
def list_change_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> List[ChangeRequest]:
    return list(
        db.execute(select(ChangeRequest).where(ChangeRequest.org_id == user.org_id)).scalars()
    )


@router.post("/{change_request_id}/approve", response_model=ChangeRequestOut)
def approve_change_request(
    change_request_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ChangeRequest:
    if user.role not in APPROVER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot approve change requests")

    change_request = db.get(ChangeRequest, change_request_id)
    if change_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
    if change_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Change request is '{change_request.status}', not 'pending'",
        )

    change_request.status = "approved"
    change_request.approved_by = user.id
    db.flush()
    return change_request


@router.post("/{change_request_id}/execute", response_model=ChangeRequestOut)
def execute_change_request_route(
    change_request_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ChangeRequest:
    if user.role not in APPROVER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot execute change requests")

    from services.actions.executor import execute_change_request

    change_request = db.get(ChangeRequest, change_request_id)
    if change_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")

    finding = db.get(Finding, change_request.finding_id)
    account = db.get(AWSAccount, finding.account_id) if finding else None
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AWS account for this finding not found")

    try:
        execute_change_request(db, change_request, account)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    db.flush()
    return change_request
