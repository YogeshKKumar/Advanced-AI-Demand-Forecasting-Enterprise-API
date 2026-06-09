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


class LiveSalesIn(BaseModel):
    date: date
    product: str = Field(..., min_length=1)
    category: str = "General"
    region: str = "All Regions"
    quantity: float = Field(..., ge=0)
    sales: float = Field(..., ge=0)


class RoleUpdateIn(BaseModel):
    role: str = Field(..., pattern="^(super_admin|analyst|viewer)$")


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


class AdvancedAnalyticsOut(BaseModel):
    revenue_prediction: float
    predicted_units: float
    inventory_risk: List[Dict[str, Any]]
    region_forecasts: List[Dict[str, Any]]
    category_insights: List[Dict[str, Any]]
    seasonal_trends: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    generated_insights: List[str]
    last_refreshed: datetime


class RealtimeSnapshotOut(BaseModel):
    dataset_id: int
    latest_sales: List[Dict[str, Any]]
    rolling_sales: float
    latest_forecast: List[ForecastPoint]
    refreshed_at: datetime


class RetrainingOut(BaseModel):
    id: int
    dataset_id: int
    selected_model: str
    previous_accuracy: float
    new_accuracy: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SearchResultsOut(BaseModel):
    datasets: List[Dict[str, Any]]
    forecasts: List[Dict[str, Any]]
    reports: List[Dict[str, Any]]
    users: List[Dict[str, Any]]


class MonitoringOut(BaseModel):
    requests_last_hour: int
    error_rate: float
    average_duration_ms: float
    slowest_endpoints: List[Dict[str, Any]]
    activity_count: int
    retraining_jobs: int
    generated_at: datetime


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


class ProfileUpdateIn(BaseModel):
    name: Optional[str] = Field(None, min_length=2)
    title: str = ""
    department: str = ""
    phone: str = ""
    preferences: Dict[str, Any] = Field(default_factory=dict)


class UserProfileOut(BaseModel):
    user: UserOut
    title: str = ""
    department: str = ""
    phone: str = ""
    preferences: Dict[str, Any] = Field(default_factory=dict)


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    token: str = Field(..., min_length=12)
    new_password: str = Field(..., min_length=6)


class ForecastScheduleIn(BaseModel):
    dataset_id: int
    name: str = Field(..., min_length=2)
    model_name: str = "ensemble"
    periods: int = Field(6, ge=1, le=36)
    interval_minutes: int = Field(1440, ge=15, le=43200)
    alert_threshold: float = Field(70, ge=0, le=100)
    is_active: bool = True


class ForecastScheduleOut(ForecastScheduleIn):
    id: int
    created_by: int
    last_run_at: Optional[datetime]
    next_run_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class IntegrationIn(BaseModel):
    name: str = Field(..., min_length=2)
    provider: str = Field(..., examples=["erp", "inventory", "external_api"])
    base_url: str = ""
    auth_type: str = "api_key"
    secret_ref: str = ""
    settings: Dict[str, Any] = Field(default_factory=dict)


class IntegrationOut(BaseModel):
    id: int
    name: str
    provider: str
    base_url: str
    auth_type: str
    status: str
    settings: Dict[str, Any]
    created_at: datetime


class WebhookIn(BaseModel):
    name: str = Field(..., min_length=2)
    url: str = Field(..., min_length=8)
    event_type: str = Field("forecast.completed")
    secret: str = ""
    is_active: bool = True


class WebhookOut(WebhookIn):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AlertRuleIn(BaseModel):
    dataset_id: Optional[int] = None
    name: str = Field(..., min_length=2)
    metric: str = Field("accuracy", pattern="^(accuracy|confidence_score|forecast_failure|low_stock)$")
    operator: str = Field("<", pattern="^(<|>|<=|>=|==)$")
    threshold: float = 75
    channel: str = Field("in_app", pattern="^(in_app|email)$")
    is_active: bool = True


class AlertRuleOut(AlertRuleIn):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardWidgetIn(BaseModel):
    widget_key: str
    title: str
    position: int = 0
    is_visible: bool = True
    settings: Dict[str, Any] = Field(default_factory=dict)


class DashboardWidgetOut(DashboardWidgetIn):
    id: int
    user_id: int


class EnterpriseInsightsOut(BaseModel):
    recommendations: List[Dict[str, Any]]
    customer_behavior: List[Dict[str, Any]]
    demand_spikes: List[Dict[str, Any]]
    low_stock_predictions: List[Dict[str, Any]]
    inventory_optimizations: List[Dict[str, Any]]
    generated_at: datetime


class ForecastTrendOut(BaseModel):
    accuracy_trends: List[Dict[str, Any]]
    historical_comparison: List[Dict[str, Any]]
    confidence_scores: List[Dict[str, Any]]
    recommendations: List[str]


class DashboardSummaryOut(BaseModel):
    dataset_id: int
    generated_at: datetime
    kpis: Dict[str, Any]
    insights: List[str]

class ForecastProjectIn(BaseModel):
    name: str = Field(..., min_length=2)
    description: str = ""


class ForecastProjectOut(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    status: str
    created_at: datetime
    dataset_count: int = 0
    forecast_count: int = 0


class ProjectMemberIn(BaseModel):
    user_id: int
    role: str = Field("editor", pattern="^(owner|editor|viewer)$")


class ProjectDatasetIn(BaseModel):
    dataset_id: int


class ProjectActivityOut(BaseModel):
    id: int
    action: str
    metadata: Dict[str, Any]
    created_at: datetime


class ScenarioIn(BaseModel):
    dataset_id: int
    name: str = Field(..., min_length=2)
    sales_growth_percent: float = Field(0, ge=-90, le=300)
    seasonality_percent: float = Field(0, ge=-80, le=200)
    demand_factor: float = Field(1, ge=0.1, le=5)
    price_change_percent: float = Field(0, ge=-90, le=300)
    cost_change_percent: float = Field(0, ge=-90, le=300)


class ScenarioOut(BaseModel):
    id: int
    project_id: int
    dataset_id: int
    name: str
    sales_growth_percent: float
    seasonality_percent: float
    demand_factor: float
    price_change_percent: float
    cost_change_percent: float
    status: str
    created_at: datetime
    results: List[Dict[str, Any]] = Field(default_factory=list)


class ScenarioComparisonOut(BaseModel):
    scenarios: List[ScenarioOut]
    totals: List[Dict[str, Any]]


class CommentIn(BaseModel):
    body: str = Field(..., min_length=1)
    run_id: Optional[int] = None


class CommentOut(BaseModel):
    id: int
    project_id: int
    run_id: Optional[int]
    user_id: int
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReportShareIn(BaseModel):
    dataset_id: Optional[int] = None
    recipient_email: EmailStr
    access_level: str = Field("view", pattern="^(view|comment|edit)$")
    expires_at: Optional[datetime] = None


class ReportShareOut(BaseModel):
    id: int
    project_id: int
    dataset_id: Optional[int]
    recipient_email: EmailStr
    access_level: str
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetVersionOut(BaseModel):
    id: int
    dataset_id: int
    version: int
    row_count: int
    change_summary: str
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetCompareOut(BaseModel):
    dataset_id: int
    versions: List[DatasetVersionOut]
    row_delta: int
    product_count: int
    category_count: int
    region_count: int


class ExecutiveDashboardOut(BaseModel):
    revenue_forecast: float
    profit_forecast: float
    estimated_cost: float
    growth_impact_percent: float
    kpis: Dict[str, Any]
    cost_analysis: List[Dict[str, Any]]
    performance: List[Dict[str, Any]]
    recommendations: List[str]


class BIInsightsOut(BaseModel):
    opportunities: List[Dict[str, Any]]
    declining_products: List[Dict[str, Any]]
    high_growth_products: List[Dict[str, Any]]
    summaries: List[str]


class AccuracyCenterOut(BaseModel):
    model_performance: List[Dict[str, Any]]
    accuracy_trends: List[Dict[str, Any]]
    historical_performance: List[Dict[str, Any]]
    improvement_summary: Dict[str, Any]
    evaluation_report: List[str]


class DashboardLayoutIn(BaseModel):
    name: str = "Executive layout"
    layout: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class DashboardLayoutOut(DashboardLayoutIn):
    id: int
    user_id: int
    created_at: datetime


class ExecutiveReportScheduleIn(BaseModel):
    project_id: int
    dataset_id: Optional[int] = None
    name: str
    frequency: str = Field("monthly", pattern="^(weekly|monthly|quarterly)$")
    report_type: str = Field("executive_summary")
    is_active: bool = True


class ExecutiveReportScheduleOut(ExecutiveReportScheduleIn):
    id: int
    created_by: int
    next_run_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
