import uuid
from datetime import datetime
from typing import Optional

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
