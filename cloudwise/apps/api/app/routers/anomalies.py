import datetime
from collections import defaultdict
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import SpendDaily, User
from ..schemas import AnomalyOut

router = APIRouter(prefix="/anomalies", tags=["anomalies"])

LOOKBACK_DAYS = 21  # recent_days + baseline_days, see services/analytics/anomalies.py defaults


@router.get("", response_model=List[AnomalyOut])
def list_anomalies(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> List[AnomalyOut]:
    from services.analytics.anomalies import detect_spend_anomalies

    start_date = datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS)
    rows = db.execute(
        select(SpendDaily.service, SpendDaily.usage_date, SpendDaily.unblended_cost).where(
            SpendDaily.org_id == user.org_id, SpendDaily.usage_date >= start_date
        )
    ).all()

    daily_by_service: dict = defaultdict(lambda: defaultdict(float))
    for service, usage_date, cost in rows:
        daily_by_service[service][usage_date] += float(cost)

    normalized = {service: list(days.items()) for service, days in daily_by_service.items()}
    anomalies = detect_spend_anomalies(normalized)

    return [
        AnomalyOut(
            service=a.service,
            baseline_daily_avg=a.baseline_daily_avg,
            recent_daily_avg=a.recent_daily_avg,
            delta_monthly=a.delta_monthly,
            since=a.since,
        )
        for a in anomalies
    ]
