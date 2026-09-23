import pathlib
import sys
from unittest.mock import MagicMock

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.notifications.slack import format_weekly_digest, send_slack_message  # noqa: E402


def test_format_weekly_digest_includes_org_name_and_totals():
    text = format_weekly_digest(
        org_name="Acme Inc",
        total_spend=18420.0,
        open_findings_count=27,
        open_savings_total=3184.0,
        top_findings=[],
        realized_savings_this_period=0.0,
    )
    assert "Acme Inc" in text
    assert "18,420.00" in text
    assert "27" in text
    assert "3,184.00" in text


def test_format_weekly_digest_lists_top_findings():
    findings = [{"resource_id": "i-abc123", "monthly_savings": 212.0, "effort": "low", "risk": "medium"}]
    text = format_weekly_digest(
        org_name="Acme Inc", total_spend=1000.0, open_findings_count=1, open_savings_total=212.0,
        top_findings=findings, realized_savings_this_period=0.0,
    )
    assert "i-abc123" in text
    assert "212.00" in text
    assert "low effort" in text
    assert "medium risk" in text


def test_format_weekly_digest_caps_top_findings_at_five():
    findings = [
        {"resource_id": f"i-{n}", "monthly_savings": float(n), "effort": "low", "risk": "low"} for n in range(10)
    ]
    text = format_weekly_digest(
        org_name="Acme", total_spend=1.0, open_findings_count=10, open_savings_total=45.0,
        top_findings=findings, realized_savings_this_period=0.0,
    )
    assert text.count("i-") == 5


def test_format_weekly_digest_mentions_no_findings_when_clean():
    text = format_weekly_digest(
        org_name="Acme", total_spend=100.0, open_findings_count=0, open_savings_total=0.0,
        top_findings=[], realized_savings_this_period=0.0,
    )
    assert "nice and tidy" in text.lower()


def test_format_weekly_digest_includes_realized_savings_when_present():
    text = format_weekly_digest(
        org_name="Acme", total_spend=100.0, open_findings_count=0, open_savings_total=0.0,
        top_findings=[], realized_savings_this_period=99.5,
    )
    assert "99.50" in text
    assert "Realized" in text


def test_send_slack_message_returns_true_on_success():
    fake_http = MagicMock()
    fake_http.post.return_value = MagicMock(raise_for_status=lambda: None)
    assert send_slack_message("https://hooks.slack.com/x", "hi", http_client=fake_http) is True


def test_send_slack_message_returns_false_on_failure_without_raising():
    fake_http = MagicMock()
    fake_http.post.side_effect = Exception("network error")
    assert send_slack_message("https://hooks.slack.com/x", "hi", http_client=fake_http) is False
