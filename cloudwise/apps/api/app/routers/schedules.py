import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import AWSAccount, Schedule, User
from ..schemas import RunSchedulesResult, ScheduleCreate, ScheduleOut

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=List[ScheduleOut])
def list_schedules(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> List[Schedule]:
    return list(db.execute(select(Schedule).where(Schedule.org_id == user.org_id)).scalars())


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Schedule:
    schedule = Schedule(org_id=user.org_id, **payload.model_dump())
    db.add(schedule)
    db.flush()
    db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    db.delete(schedule)


@router.post("/run", response_model=RunSchedulesResult)
def run_schedules_now(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> RunSchedulesResult:
    """Manually trigger evaluation of this org's schedules (a real deployment
    would call services.actions.scheduler.run_due_schedules from a periodic
    worker instead — see that module's docstring).
    """
    from services.actions.scheduler import run_due_schedules

    schedules = list(db.execute(select(Schedule).where(Schedule.org_id == user.org_id)).scalars())
    if not schedules:
        return RunSchedulesResult(evaluated=0, actions_taken=0)

    account_ids = {s.account_id for s in schedules}
    accounts = db.execute(select(AWSAccount).where(AWSAccount.id.in_(account_ids))).scalars().all()
    accounts_by_id = {a.id: a for a in accounts}

    results = run_due_schedules(db, user.org_id, schedules, accounts_by_id)
    return RunSchedulesResult(evaluated=len(schedules), actions_taken=len(results))
