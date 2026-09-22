from dataclasses import dataclass, field
from typing import Any, Dict, Literal

Effort = Literal["low", "medium", "high"]
Risk = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class Finding:
    """One waste finding. monthly_savings is always computed here in plain
    arithmetic from inputs the caller already measured (hours, GB, $/unit) —
    never by an LLM. See services/rules/*.py for the formula behind each rule.
    """

    rule_id: str
    resource_id: str
    resource_type: str
    monthly_savings: float
    effort: Effort
    risk: Risk
    fix: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.monthly_savings < 0:
            raise ValueError(f"monthly_savings must be >= 0, got {self.monthly_savings}")


HOURS_PER_MONTH = 730  # AWS's own standard approximation (365.25 * 24 / 12)
