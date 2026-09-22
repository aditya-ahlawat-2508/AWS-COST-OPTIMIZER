import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
