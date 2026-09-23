"""Weekly Slack digest (blueprint's Notifier component). Formatting is a pure
function so the exact text is unit-testable without a network call; sending
is a thin wrapper over a Slack incoming webhook (a plain POST of JSON), not
the full Slack SDK — one HTTP call doesn't need an SDK.
"""
from typing import Any, Dict, List, Optional

import requests


def format_weekly_digest(
    org_name: str,
    total_spend: float,
    open_findings_count: int,
    open_savings_total: float,
    top_findings: List[Dict[str, Any]],
    realized_savings_this_period: float,
) -> str:
    lines = [
        f"*CloudWise weekly digest — {org_name}*",
        f"Spend (last 30d): *${total_spend:,.2f}*",
        f"Open findings: *{open_findings_count}* worth *${open_savings_total:,.2f}/mo*",
    ]
    if realized_savings_this_period > 0:
        lines.append(f"Realized this week: *${realized_savings_this_period:,.2f}/mo*")

    if top_findings:
        lines.append("\n*Top recommendations:*")
        for finding in top_findings[:5]:
            lines.append(
                f"• `{finding['resource_id']}` — ${finding['monthly_savings']:,.2f}/mo "
                f"({finding['effort']} effort, {finding['risk']} risk)"
            )
    else:
        lines.append("\nNo open findings — nice and tidy.")

    return "\n".join(lines)


def send_slack_message(webhook_url: str, text: str, http_client: Any = requests) -> bool:
    """Returns True on success. Failures (bad webhook, Slack outage) are
    swallowed to False rather than raised — a notification failing must
    never take down whatever triggered it (a scan, a scheduled job).
    """
    try:
        response = http_client.post(webhook_url, json={"text": text}, timeout=10)
        response.raise_for_status()
        return True
    except Exception:
        return False
