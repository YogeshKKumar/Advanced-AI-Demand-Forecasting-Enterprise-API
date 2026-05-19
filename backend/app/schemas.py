from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, examples=["Yogeshwaran K"])
    email: EmailStr = Field(..., examples=["admin@forecast.ai"])
    password: str = Field(..., min_length=6, examples=["Forecast@123"])


class UserLogin(BaseModel):
    email: EmailStr = Field(..., examples=["admin@forecast.ai"])
    password: str = Field(..., examples=["Forecast@123"])


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DatasetOut(BaseModel):
    id: int
    name: str
    row_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedDatasets(BaseModel):
    items: List[DatasetOut]
    total: int
    page: int
    page_size: int
    pages: int


class DatasetUploadResponse(BaseModel):
    dataset: DatasetOut
    validation: Dict[str, Any]


class ForecastRequest(BaseModel):
    periods: int = Field(6, ge=1, le=36, examples=[12])
    model_name: str = Field("linear_regression", examples=["random_forest"])


class ForecastPoint(BaseModel):
    date: date
    product: str
    predicted_demand: float
    lower_bound: float
    upper_bound: float
    accuracy: float
    confidence_score: float
    model_name: str


class ForecastRunOut(BaseModel):
    id: int
    dataset_id: int
    model_name: str
    periods: int
    status: str
    rmse: float
    mae: float
    accuracy: float
    confidence_score: float
    total_predictions: int
    created_at: datetime

    class Config:
        from_attributes = True


class ForecastResponse(BaseModel):
    run: ForecastRunOut
    items: List[ForecastPoint]


class ModelMetricOut(BaseModel):
    model_name: str
    product: str
    rmse: float
    mae: float
    accuracy: float
    confidence_score: float

    class Config:
        from_attributes = True


class ModelComparisonItem(BaseModel):
    model_name: str
    average_rmse: float
    average_mae: float
    average_accuracy: float
    confidence_score: float
    products: List[Dict[str, Any]]


class AnalyticsOut(BaseModel):
    total_sales: float
    total_units: float
    average_order_value: float
    monthly_sales: List[Dict[str, Any]]
    top_products: List[Dict[str, Any]]
    sales_by_category: List[Dict[str, Any]]
    sales_by_region: List[Dict[str, Any]]
    forecast_accuracy: float
    confidence_score: float
    forecast: List[ForecastPoint]
    recent_activity: List[Dict[str, Any]]
    filters: Dict[str, Any]


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityOut(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: Optional[int]
    metadata: Dict[str, Any]
    created_at: datetime


class AdminSummary(BaseModel):
    total_users: int
    total_datasets: int
    total_records: int
    total_forecast_runs: int
    total_reports: int
    active_users: int
    recent_activity: List[Dict[str, Any]]
    model_usage: List[Dict[str, Any]]


class ReportSummary(BaseModel):
    dataset: DatasetOut
    latest_run: Optional[ForecastRunOut]
    metrics: List[ModelMetricOut]
    forecast: List[ForecastPoint]
