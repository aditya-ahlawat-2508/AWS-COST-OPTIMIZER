import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    role: str


class AWSAccountCreate(BaseModel):
    aws_account_id: str = Field(pattern=r"^\d{12}$")
    role_arn: str
    external_id: str
    label: Optional[str] = None


class AWSAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    aws_account_id: str
    role_arn: str
    label: Optional[str]
    status: str
    created_at: datetime


class ScanResult(BaseModel):
    resources_scanned: int
    findings_written: int
    regions_scanned: List[str]


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    rule_id: str
    resource_id: str
    resource_type: str
    monthly_savings: float
    effort: str
    risk: str
    status: str


class CopilotChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class CopilotChatResponse(BaseModel):
    text: str
    tool_calls: List[str]
    grounding_warnings: List[str]


class AnomalyOut(BaseModel):
    service: str
    baseline_daily_avg: float
    recent_daily_avg: float
    delta_monthly: float
    since: date


class BudgetCreate(BaseModel):
    name: str = Field(min_length=1)
    monthly_limit_usd: float = Field(gt=0)
    account_id: Optional[uuid.UUID] = None


class BudgetOut(BaseModel):
    id: uuid.UUID
    account_id: Optional[uuid.UUID]
    name: str
    monthly_limit_usd: float
    spent_this_month: float


class ScheduleCreate(BaseModel):
    account_id: uuid.UUID
    resource_id: str = Field(min_length=1)
    resource_type: str = Field(default="ec2_instance", pattern=r"^ec2_instance$")
    timezone: str = Field(default="UTC")
    start_hour: int = Field(ge=0, lt=24)
    stop_hour: int = Field(gt=0, le=24)
    weekdays_only: bool = True
    enabled: bool = True

    @model_validator(mode="after")
    def _check_hour_window(self) -> "ScheduleCreate":
        if self.start_hour >= self.stop_hour:
            raise ValueError("start_hour must be before stop_hour")
        return self


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    resource_id: str
    resource_type: str
    timezone: str
    start_hour: int
    stop_hour: int
    weekdays_only: bool
    enabled: bool
    created_at: datetime


class RunSchedulesResult(BaseModel):
    evaluated: int
    actions_taken: int


class NotificationSettingsOut(BaseModel):
    slack_webhook_url: Optional[str]


class NotificationSettingsUpdate(BaseModel):
    slack_webhook_url: Optional[str] = None


class SendDigestResult(BaseModel):
    sent: bool


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: Optional[uuid.UUID]
    action: str
    details: dict
    created_at: datetime


class ChangeRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    action_type: str
    status: str
    rollback_plan: Optional[str]
    execution_result: Optional[dict]
    executed_at: Optional[datetime]
    created_at: datetime


class CheckoutRequest(BaseModel):
    tier: str = Field(pattern=r"^(starter|growth)$")
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class RazorpayCheckoutRequest(BaseModel):
    tier: str = Field(pattern=r"^(starter|growth)$")


class EntitlementOut(BaseModel):
    tier: str
    status: str
    max_accounts: Optional[int]


class VerifiedSavingsOut(BaseModel):
    service: str
    before_daily_avg: float
    after_daily_avg: float
    verified_monthly_savings: float
    before_days: int
    after_days: int


class SpendByGroup(BaseModel):
    key: str
    cost: float


class SpendSummary(BaseModel):
    start_date: date
    end_date: date
    view: str
    group_by: str
    currency: str
    total_cost: float
    breakdown: List[SpendByGroup]
