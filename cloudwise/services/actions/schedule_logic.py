"""Pure office-hours scheduling logic (blueprint Section 06: "Schedules:
office-hours start/stop for tagged non-prod resources"). Deliberately
separated from anything that talks to AWS or a DB — see scheduler.py for
that — so the actual decision ("should this be running right now") is
exactly reproducible and unit-testable without a clock or a network call.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Schedule:
    id: str
    resource_id: str
    resource_type: str  # only "ec2_instance" is wired to an executor today
    timezone: str
    start_hour: int  # local hour (0-23) the resource should start running
    stop_hour: int  # local hour it should stop; must be > start_hour
    weekdays_only: bool
    enabled: bool

    def __post_init__(self) -> None:
        if not (0 <= self.start_hour < self.stop_hour <= 24):
            raise ValueError(f"invalid schedule window: start_hour={self.start_hour}, stop_hour={self.stop_hour}")


def is_within_office_hours(schedule: Schedule, now_utc: datetime) -> bool:
    if not schedule.enabled:
        return False
    local_now = now_utc.astimezone(ZoneInfo(schedule.timezone))
    if schedule.weekdays_only and local_now.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False
    return schedule.start_hour <= local_now.hour < schedule.stop_hour


def due_action(schedule: Schedule, now_utc: datetime, current_state: str) -> Optional[str]:
    """current_state: the resource's actual live state ("running", "stopped",
    etc). Returns "start" or "stop" if the schedule and live state disagree,
    else None — callers should only act when this returns non-None, which
    also makes re-running the same evaluation twice in a row a safe no-op.
    """
    should_be_running = is_within_office_hours(schedule, now_utc)
    if should_be_running and current_state != "running":
        return "start"
    if not should_be_running and current_state == "running":
        return "stop"
    return None
