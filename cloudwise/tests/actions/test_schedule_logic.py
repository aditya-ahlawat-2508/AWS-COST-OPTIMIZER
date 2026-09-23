from datetime import datetime, timezone

import pytest

from services.actions.schedule_logic import Schedule, due_action, is_within_office_hours


def _schedule(**overrides):
    base = dict(
        id="sched-1",
        resource_id="i-abc123",
        resource_type="ec2_instance",
        timezone="America/New_York",
        start_hour=9,
        stop_hour=18,
        weekdays_only=True,
        enabled=True,
    )
    base.update(overrides)
    return Schedule(**base)


def test_within_office_hours_on_a_weekday():
    schedule = _schedule()
    # 2026-09-23 is a Wednesday; 14:00 UTC = 10:00 America/New_York
    now = datetime(2026, 9, 23, 14, 0, tzinfo=timezone.utc)
    assert is_within_office_hours(schedule, now) is True


def test_outside_office_hours_at_night():
    schedule = _schedule()
    now = datetime(2026, 9, 23, 2, 0, tzinfo=timezone.utc)  # ~22:00 the prior night in NY
    assert is_within_office_hours(schedule, now) is False


def test_weekend_is_never_in_office_hours_when_weekdays_only():
    schedule = _schedule()
    # 2026-09-26 is a Saturday, same hour that's a weekday pass above.
    now = datetime(2026, 9, 26, 14, 0, tzinfo=timezone.utc)
    assert is_within_office_hours(schedule, now) is False


def test_weekend_included_when_weekdays_only_is_false():
    schedule = _schedule(weekdays_only=False)
    now = datetime(2026, 9, 26, 14, 0, tzinfo=timezone.utc)
    assert is_within_office_hours(schedule, now) is True


def test_disabled_schedule_is_never_in_office_hours():
    schedule = _schedule(enabled=False)
    now = datetime(2026, 9, 23, 14, 0, tzinfo=timezone.utc)
    assert is_within_office_hours(schedule, now) is False


def test_rejects_invalid_hour_window():
    with pytest.raises(ValueError):
        _schedule(start_hour=18, stop_hour=9)


def test_due_action_returns_start_when_should_run_but_stopped():
    schedule = _schedule()
    now = datetime(2026, 9, 23, 14, 0, tzinfo=timezone.utc)  # within office hours
    assert due_action(schedule, now, current_state="stopped") == "start"


def test_due_action_returns_stop_when_should_not_run_but_running():
    schedule = _schedule()
    now = datetime(2026, 9, 23, 2, 0, tzinfo=timezone.utc)  # outside office hours
    assert due_action(schedule, now, current_state="running") == "stop"


def test_due_action_returns_none_when_state_already_matches():
    schedule = _schedule()
    now = datetime(2026, 9, 23, 14, 0, tzinfo=timezone.utc)
    assert due_action(schedule, now, current_state="running") is None

    now_night = datetime(2026, 9, 23, 2, 0, tzinfo=timezone.utc)
    assert due_action(schedule, now_night, current_state="stopped") is None


def test_due_action_is_idempotent_across_repeated_calls():
    schedule = _schedule()
    now = datetime(2026, 9, 23, 14, 0, tzinfo=timezone.utc)
    first = due_action(schedule, now, current_state="stopped")
    assert first == "start"
    # Once "started", a second evaluation at the same moment must be a no-op.
    second = due_action(schedule, now, current_state="running")
    assert second is None
