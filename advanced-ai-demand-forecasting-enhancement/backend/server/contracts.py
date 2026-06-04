from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    full_name: str = Field(..., examples=["Priya"])
    email: EmailStr = Field(..., examples=["priya@forecast.ai"])
    password: str = Field(..., min_length=6, examples=["Priya@123"])


class SigninIn(BaseModel):
    email: EmailStr = Field(..., examples=["priya@forecast.ai"])
    password: str = Field(..., examples=["Priya@123"])


class AccountOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    active: bool

    class Config:
        from_attributes = True


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account: AccountOut


class WorkbookOut(BaseModel):
    id: int
    title: str
    rows_loaded: int
    state: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class WorkbookPage(BaseModel):
    records: List[WorkbookOut]
    total: int
    page: int
    size: int


class UploadOut(BaseModel):
    workbook: WorkbookOut
    profile: Dict[str, Any]


class ScenarioIn(BaseModel):
    algorithm: str = Field("linear", examples=["forest"])
    horizon: int = Field(6, ge=1, le=24, examples=[9])


class ProjectionOut(BaseModel):
    target_date: date
    item_name: str
    expected_units: float
    low_estimate: float
    high_estimate: float
    confidence: float


class ScenarioOut(BaseModel):
    id: int
    workbook_id: int
    algorithm: str
    horizon: int
    rmse: float
    mae: float
    quality_score: float
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


class ScenarioResult(BaseModel):
    scenario: ScenarioOut
    projections: List[ProjectionOut]


class CompareOut(BaseModel):
    algorithm: str
    rmse: float
    mae: float
    quality_score: float
    confidence: float


class InsightOut(BaseModel):
    revenue: float
    units: float
    avg_value: float
    quality_score: float
    confidence: float
    monthly_revenue: List[Dict[str, Any]]
    segment_mix: List[Dict[str, Any]]
    market_mix: List[Dict[str, Any]]
    top_items: List[Dict[str, Any]]
    projections: List[ProjectionOut]
    audit_trail: List[Dict[str, Any]]


class AlertOut(BaseModel):
    id: int
    headline: str
    detail: str
    level: str
    seen: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AdminOut(BaseModel):
    accounts: int
    workbooks: int
    observations: int
    scenarios: int
    alerts: int
    recent_events: List[Dict[str, Any]]
