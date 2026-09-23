"""Daily spend anomaly detection (blueprint Section 04's "Anomaly detector":
a daily spend model, not an ML service). Compares each service's recent
average daily cost against its own prior baseline — simple, explainable,
and exactly reproducible, which matters more here than sophistication: a
customer asking "why did you flag this" deserves an arithmetic answer.
"""
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Tuple

DEFAULT_RECENT_DAYS = 7
DEFAULT_BASELINE_DAYS = 14
DEFAULT_RELATIVE_THRESHOLD = 0.3  # recent avg must be >=30% above baseline
DEFAULT_MIN_ABSOLUTE_DELTA_PER_DAY = 2.0  # and at least $2/day, to ignore noise on tiny services


@dataclass(frozen=True)
class SpendAnomaly:
    service: str
    baseline_daily_avg: float
    recent_daily_avg: float
    delta_monthly: float
    since: date


def detect_spend_anomalies(
    daily_by_service: Dict[str, List[Tuple[date, float]]],
    recent_days: int = DEFAULT_RECENT_DAYS,
    baseline_days: int = DEFAULT_BASELINE_DAYS,
    relative_threshold: float = DEFAULT_RELATIVE_THRESHOLD,
    min_absolute_delta_per_day: float = DEFAULT_MIN_ABSOLUTE_DELTA_PER_DAY,
) -> List[SpendAnomaly]:
    """daily_by_service: {service_name: [(date, cost), ...]}, any order,
    ideally covering at least recent_days + baseline_days of history per
    service. Services with less history than that are skipped, not guessed at.
    """
    anomalies = []
    for service, points in daily_by_service.items():
        points = sorted(points, key=lambda p: p[0])
        if len(points) < recent_days + baseline_days:
            continue

        recent = points[-recent_days:]
        baseline = points[-(recent_days + baseline_days): -recent_days]
        recent_avg = sum(cost for _, cost in recent) / len(recent)
        baseline_avg = sum(cost for _, cost in baseline) / len(baseline)
        delta_per_day = recent_avg - baseline_avg

        if delta_per_day < min_absolute_delta_per_day:
            continue
        relative_increase = float("inf") if baseline_avg == 0 else delta_per_day / baseline_avg
        if relative_increase < relative_threshold:
            continue

        anomalies.append(
            SpendAnomaly(
                service=service,
                baseline_daily_avg=round(baseline_avg, 2),
                recent_daily_avg=round(recent_avg, 2),
                delta_monthly=round(delta_per_day * 30, 2),
                since=recent[0][0],
            )
        )

    anomalies.sort(key=lambda a: a.delta_monthly, reverse=True)
    return anomalies
