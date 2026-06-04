from __future__ import annotations

from collections import defaultdict, deque

from io import BytesIO
from datetime import datetime, timedelta
from math import ceil
from time import monotonic, perf_counter
from typing import List, Optional

import pandas as pd
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, hash_password, require_admin, require_analyst, verify_password
from .cache import dashboard_cache
from .database import Base, SessionLocal, engine, get_db
from .models import AlertRule, ApiMetric, ActivityLog, DashboardWidget, Dataset, ForecastRun, ForecastSchedule, Integration, ModelMetric, Notification, PasswordResetToken, ReportJob, RetrainingJob, SalesRecord, User, UserProfile, WebhookSubscription
from .schemas import (
    ActivityOut,
    AdminSummary,
    AdvancedAnalyticsOut,
    AnalyticsOut,
    DatasetOut,
    DatasetUploadResponse,
    ForecastRequest,
    ForecastResponse,
    ForecastRunOut,
    LiveSalesIn,
    ModelComparisonItem,
    MonitoringOut,
    NotificationOut,
    PaginatedDatasets,
    ReportSummary,
    RealtimeSnapshotOut,
    RetrainingOut,
    RoleUpdateIn,
    SearchResultsOut,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
    AlertRuleIn,
    AlertRuleOut,
    DashboardSummaryOut,
    DashboardWidgetIn,
    DashboardWidgetOut,
    EnterpriseInsightsOut,
    ForecastScheduleIn,
    ForecastScheduleOut,
    ForecastTrendOut,
    IntegrationIn,
    IntegrationOut,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    ProfileUpdateIn,
    UserProfileOut,
    WebhookIn,
    WebhookOut,
)
from .services import (
    SUPPORTED_MODELS,
    advanced_analytics_payload,
    automatically_retrain,
    analytics_payload,
    build_excel_report,
    build_pdf_report,
    compare_models,
    detect_anomalies,
    forecast_points,
    get_user_dataset,
    log_activity,
    normalize_dataset,
    notify,
    realtime_snapshot,
    seasonal_trends,
    train_and_forecast,
    create_default_widgets,
    enterprise_ai_insights,
    evaluate_alert_rules,
    forecast_trend_payload,
    run_due_forecast_schedules,
)
from .settings import settings


Base.metadata.create_all(bind=engine)


def migrate_phase_four_roles() -> None:
    with engine.begin() as connection:
        connection.execute(text("UPDATE users SET role = 'super_admin' WHERE role = 'admin'"))


migrate_phase_four_roles()

app = FastAPI(
    title=settings.app_name,
    version="4.0.0",
    description=(
        "Modern enterprise-level full-stack AI forecasting API with JWT security, role-based access, "
        "Linear Regression, Random Forest, XGBoost, Prophet, Ensemble AI, real-time monitoring, automated retraining, "
        "anomaly detection, seasonal signals, analytics caching, activity telemetry, notifications, admin APIs, "
        "Excel/PDF exports, and detailed Swagger examples. Developed by Yogeshwaran K.\n\n"
        "Example authenticated request:\n"
        "```bash\n"
        "curl -X GET http://localhost:8000/api/datasets?page=1&page_size=10 \\\n"
        "  -H \"Authorization: Bearer <ACCESS_TOKEN>\" \\\n"
        "  -H \"Accept: application/json\"\n"
        "```"
    ),
    contact={"name": "Yogeshwaran K", "url": "http://localhost:5173"},
    openapi_tags=[
        {"name": "Authentication", "description": "Register, login, and profile APIs with JWT bearer tokens."},
        {"name": "Datasets", "description": "Upload, search, filter, sort, and paginate demand datasets."},
        {"name": "Forecasting", "description": "Train AI models, compare algorithms, and view forecast history."},
        {"name": "Analytics", "description": "Dashboard metrics, charts, and filterable insights."},
        {"name": "Reports", "description": "Excel and PDF report exports with realistic forecast metrics."},
        {"name": "Notifications", "description": "User notification center APIs."},
        {"name": "Admin", "description": "Role-protected enterprise admin management APIs."},
        {"name": "Realtime", "description": "Live sales monitoring and automatic forecast refresh."},
        {"name": "Optimization", "description": "Model retraining, anomalies, and seasonality intelligence."},
        {"name": "Monitoring", "description": "System performance and API usage visibility."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_windows = defaultdict(deque)


@app.middleware("http")
async def api_rate_limiter(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    client = request.client.host if request.client else "unknown"
    key = f"{client}:{request.url.path.split('/')[2] if len(request.url.path.split('/')) > 2 else 'api'}"
    now = monotonic()
    window = _rate_windows[key]
    while window and now - window[0] > settings.rate_limit_window_seconds:
        window.popleft()
    if len(window) >= settings.rate_limit_requests:
        return JSONResponse(status_code=429, content={"success": False, "error": "Rate limit exceeded", "status_code": 429})
    window.append(now)
    return await call_next(request)


@app.middleware("http")
async def api_performance_monitor(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        duration_ms = round((perf_counter() - started) * 1000, 2)
        db = SessionLocal()
        try:
            db.add(ApiMetric(endpoint=request.url.path, method=request.method, status_code=response.status_code, duration_ms=duration_ms))
            db.commit()
        finally:
            db.close()
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail, "status_code": exc.status_code})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"success": False, "error": "Internal server error", "detail": str(exc)})


@app.get("/api/health", tags=["System"], summary="Enterprise API health check")
async def health():
    return {"status": "healthy", "service": settings.app_name, "version": settings.app_version}


@app.post(
    "/api/auth/register",
    response_model=Token,
    tags=["Authentication"],
    summary="Register a new user",
    description="Creates an analyst account. The first registered user is automatically assigned the Super Admin role.",
    responses={200: {"description": "JWT token and user profile returned after registration"}},
)
async def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    role = "super_admin" if db.query(User).count() == 0 else "analyst"
    user = User(name=payload.name, email=payload.email, hashed_password=hash_password(payload.password), role=role)
    db.add(user)
    db.flush()
    notify(db, user.id, "Welcome to Enterprise Forecasting", "Your AI forecasting workspace is ready.", "success")
    log_activity(db, user.id, "user.registered", "user", user.id, {"role": role})
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user.email, user.role), "user": user}


@app.post("/api/auth/login", response_model=Token, tags=["Authentication"], summary="Login and receive JWT token")
async def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    log_activity(db, user.id, "user.login", "user", user.id)
    db.commit()
    return {"access_token": create_access_token(user.email, user.role), "user": user}


@app.get("/api/auth/me", response_model=UserOut, tags=["Authentication"], summary="Current user profile")
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/api/datasets", response_model=PaginatedDatasets, tags=["Datasets"], summary="Search, filter, sort, and paginate datasets")
async def list_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = "",
    status: str = "",
    sort_by: str = Query("created_at", pattern="^(created_at|name|row_count|status)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Dataset)
    if current_user.role not in {"admin", "super_admin"}:
        query = query.filter(Dataset.owner_id == current_user.id)
    if search:
        query = query.filter(Dataset.name.ilike(f"%{search}%"))
    if status:
        query = query.filter(Dataset.status == status)
    total = query.count()
    sort_column = getattr(Dataset, sort_by)
    query = query.order_by(sort_column.asc() if sort_dir == "asc" else sort_column.desc())
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": ceil(total / page_size) if total else 0}


@app.post("/api/datasets/upload", response_model=DatasetUploadResponse, tags=["Datasets"], summary="Upload CSV or Excel dataset")
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit")
    try:
        if not file.filename:
            raise ValueError("File name is required")
        if file.filename.lower().endswith(".csv"):
            df = pd.read_csv(BytesIO(content))
        elif file.filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Only CSV and Excel files are supported")
        clean_df, stats = normalize_dataset(df)
    except Exception as exc:
        notify(db, current_user.id, "Dataset upload failed", str(exc), "error")
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    dataset = Dataset(name=file.filename, row_count=len(clean_df), owner_id=current_user.id, status="ready")
    db.add(dataset)
    db.flush()
    db.bulk_save_objects([
        SalesRecord(
            dataset_id=dataset.id,
            date=row.date.date(),
            product=row.product,
            category=row.category,
            region=row.region,
            quantity=float(row.quantity),
            sales=float(row.sales),
        )
        for row in clean_df.itertuples(index=False)
    ])
    notify(db, current_user.id, "Dataset uploaded", f"{dataset.name} is ready with {dataset.row_count} clean rows.", "success")
    log_activity(db, current_user.id, "dataset.uploaded", "dataset", dataset.id, stats)
    dashboard_cache.invalidate_prefix(f"analytics:{dataset.id}:")
    background_tasks.add_task(lambda: None)
    db.commit()
    db.refresh(dataset)
    return {"dataset": dataset, "validation": stats}


@app.get("/api/datasets/{dataset_id}/filters", tags=["Datasets"], summary="Distinct values for dashboard filters")
async def dataset_filters(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    base = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id)
    return {
        "products": [row[0] for row in base.with_entities(SalesRecord.product).distinct().order_by(SalesRecord.product).all()],
        "categories": [row[0] for row in base.with_entities(SalesRecord.category).distinct().order_by(SalesRecord.category).all()],
        "regions": [row[0] for row in base.with_entities(SalesRecord.region).distinct().order_by(SalesRecord.region).all()],
    }


@app.get("/api/forecast/models", tags=["Forecasting"], summary="Supported AI forecasting models")
async def forecast_models():
    return {"items": [{"name": item, "label": item.replace("_", " ").title()} for item in SUPPORTED_MODELS]}


@app.post("/api/forecast/{dataset_id}", response_model=ForecastResponse, tags=["Forecasting"], summary="Train model and create forecast")
async def forecast(dataset_id: int, payload: ForecastRequest, current_user: User = Depends(require_analyst), db: Session = Depends(get_db)):
    dataset = get_user_dataset(db, dataset_id, current_user)
    run = train_and_forecast(db, dataset.id, payload.periods, payload.model_name)
    notify(db, current_user.id, "Forecast completed", f"{dataset.name} generated {run.total_predictions} predictions using {run.model_name}.", "success")
    log_activity(db, current_user.id, "forecast.completed", "dataset", dataset.id, {"model": run.model_name, "accuracy": run.accuracy, "confidence": run.confidence_score})
    dashboard_cache.invalidate_prefix(f"analytics:{dataset.id}:")
    db.commit()
    db.refresh(run)
    return {"run": run, "items": forecast_points(run)}


@app.get("/api/forecast/{dataset_id}/compare", response_model=List[ModelComparisonItem], tags=["Forecasting"], summary="Compare forecasting models")
async def forecast_model_comparison(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    return compare_models(db, dataset_id)


@app.get("/api/forecast/{dataset_id}/history", response_model=List[ForecastRunOut], tags=["Forecasting"], summary="Forecast run history")
async def forecast_history(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    return db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset_id).order_by(ForecastRun.created_at.desc()).limit(50).all()


@app.get("/api/realtime/{dataset_id}/snapshot", response_model=RealtimeSnapshotOut, tags=["Realtime"], summary="Live demand and forecast snapshot")
async def live_snapshot(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    return realtime_snapshot(db, dataset_id)


@app.post("/api/realtime/{dataset_id}/sales", tags=["Realtime"], summary="Ingest real-time sales event")
async def live_sale(dataset_id: int, payload: LiveSalesIn, current_user: User = Depends(require_analyst), db: Session = Depends(get_db)):
    dataset = get_user_dataset(db, dataset_id, current_user)
    record = SalesRecord(dataset_id=dataset.id, date=payload.date, product=payload.product, category=payload.category, region=payload.region, quantity=payload.quantity, sales=payload.sales)
    db.add(record)
    dataset.row_count += 1
    log_activity(db, current_user.id, "sales.realtime.ingested", "dataset", dataset.id, {"product": payload.product, "quantity": payload.quantity})
    dashboard_cache.invalidate_prefix(f"analytics:{dataset.id}:")
    db.commit()
    return {"success": True, "record_id": record.id, "snapshot": realtime_snapshot(db, dataset.id)}


@app.post("/api/realtime/{dataset_id}/auto-refresh", response_model=ForecastResponse, tags=["Realtime"], summary="Refresh forecast using ensemble AI")
async def auto_refresh_forecast(dataset_id: int, periods: int = Query(6, ge=1, le=36), current_user: User = Depends(require_analyst), db: Session = Depends(get_db)):
    dataset = get_user_dataset(db, dataset_id, current_user)
    run = train_and_forecast(db, dataset.id, periods, "ensemble")
    notify(db, current_user.id, "Live forecast refreshed", f"Ensemble model refreshed {dataset.name} with {run.accuracy}% accuracy.", "success")
    log_activity(db, current_user.id, "forecast.realtime.refreshed", "dataset", dataset.id, {"model": "ensemble", "accuracy": run.accuracy})
    dashboard_cache.invalidate_prefix(f"analytics:{dataset.id}:")
    db.commit()
    db.refresh(run)
    return {"run": run, "items": forecast_points(run)}


@app.get("/api/analytics/{dataset_id}", response_model=AnalyticsOut, tags=["Analytics"], summary="Dashboard analytics with advanced filters")
async def analytics(
    dataset_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: str = "",
    region: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_user_dataset(db, dataset_id, current_user)
    cache_key = f"analytics:{dataset_id}:{start_date}:{end_date}:{category}:{region}"
    cached = dashboard_cache.get(cache_key)
    if cached:
        return cached
    return dashboard_cache.set(cache_key, analytics_payload(db, dataset_id, start_date, end_date, category, region))


@app.get("/api/analytics/{dataset_id}/advanced", response_model=AdvancedAnalyticsOut, tags=["Analytics"], summary="Revenue, region, category and inventory intelligence")
async def advanced_analytics(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    key = f"analytics:{dataset_id}:advanced"
    return dashboard_cache.get(key) or dashboard_cache.set(key, advanced_analytics_payload(db, dataset_id))


@app.get("/api/optimization/{dataset_id}/anomalies", tags=["Optimization"], summary="Detect unusual sales patterns")
async def anomalies(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    return {"items": detect_anomalies(db, dataset_id)}


@app.get("/api/optimization/{dataset_id}/seasonality", tags=["Optimization"], summary="Seasonal sales trend signals")
async def seasonality(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    return {"items": seasonal_trends(db, dataset_id)}


@app.post("/api/optimization/{dataset_id}/retrain", response_model=RetrainingOut, tags=["Optimization"], summary="Automatically retrain and select the strongest model")
async def retrain(dataset_id: int, periods: int = Query(6, ge=1, le=36), current_user: User = Depends(require_analyst), db: Session = Depends(get_db)):
    dataset = get_user_dataset(db, dataset_id, current_user)
    job = automatically_retrain(db, dataset.id, current_user.id, periods)
    notify(db, current_user.id, "AI retraining completed", f"{job.selected_model} selected with {job.new_accuracy}% accuracy.", "success")
    log_activity(db, current_user.id, "model.retrained", "dataset", dataset.id, {"selected_model": job.selected_model, "accuracy": job.new_accuracy})
    dashboard_cache.invalidate_prefix(f"analytics:{dataset.id}:")
    db.commit()
    db.refresh(job)
    return job


@app.get("/api/search", response_model=SearchResultsOut, tags=["Analytics"], summary="Global enterprise search")
async def global_search(q: str = Query(..., min_length=1), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset_query = db.query(Dataset).filter(Dataset.name.ilike(f"%{q}%"))
    if current_user.role not in {"admin", "super_admin"}:
        dataset_query = dataset_query.filter(Dataset.owner_id == current_user.id)
    datasets = dataset_query.order_by(Dataset.created_at.desc()).limit(8).all()
    permitted_ids = [item.id for item in datasets]
    forecast_query = db.query(ForecastRun, Dataset).join(Dataset, ForecastRun.dataset_id == Dataset.id).filter(ForecastRun.model_name.ilike(f"%{q}%"))
    if current_user.role not in {"admin", "super_admin"}:
        forecast_query = forecast_query.filter(Dataset.owner_id == current_user.id)
    forecasts = forecast_query.order_by(ForecastRun.created_at.desc()).limit(8).all()
    users = []
    if current_user.role in {"admin", "super_admin"}:
        users = [{"id": user.id, "name": user.name, "email": user.email, "role": user.role} for user in db.query(User).filter((User.name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%"))).limit(8).all()]
    return {
        "datasets": [{"id": item.id, "name": item.name, "row_count": item.row_count, "status": item.status} for item in datasets],
        "forecasts": [{"id": run.id, "dataset": dataset.name, "model_name": run.model_name, "accuracy": run.accuracy} for run, dataset in forecasts],
        "reports": [{"dataset_id": item.id, "name": f"{item.name} analytics summary"} for item in datasets if item.id in permitted_ids],
        "users": users,
    }


@app.get("/api/activity", response_model=List[ActivityOut], tags=["Analytics"], summary="Recent activity logs")
async def activities(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(ActivityLog)
    if current_user.role not in {"admin", "super_admin"}:
        query = query.filter(ActivityLog.user_id == current_user.id)
    items = query.order_by(ActivityLog.created_at.desc()).limit(40).all()
    return [{"id": item.id, "action": item.action, "entity_type": item.entity_type, "entity_id": item.entity_id, "metadata": __import__("json").loads(item.metadata_json), "created_at": item.created_at} for item in items]


@app.get("/api/monitoring/metrics", response_model=MonitoringOut, tags=["Monitoring"], summary="API and system performance metrics")
async def system_metrics(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=1)
    base = db.query(ApiMetric).filter(ApiMetric.created_at >= since)
    requests = base.count()
    errors = base.filter(ApiMetric.status_code >= 400).count()
    duration = db.query(func.avg(ApiMetric.duration_ms)).filter(ApiMetric.created_at >= since).scalar() or 0
    grouped = db.query(ApiMetric.endpoint, func.avg(ApiMetric.duration_ms).label("average_ms"), func.count(ApiMetric.id).label("calls")).filter(ApiMetric.created_at >= since).group_by(ApiMetric.endpoint).order_by(func.avg(ApiMetric.duration_ms).desc()).limit(6).all()
    return {
        "requests_last_hour": requests,
        "error_rate": round(errors / max(requests, 1) * 100, 2),
        "average_duration_ms": round(float(duration), 2),
        "slowest_endpoints": [{"endpoint": row.endpoint, "average_ms": round(float(row.average_ms), 2), "calls": row.calls} for row in grouped],
        "activity_count": db.query(ActivityLog).count(),
        "retraining_jobs": db.query(RetrainingJob).count(),
        "generated_at": datetime.utcnow(),
    }


@app.get("/api/notifications", response_model=List[NotificationOut], tags=["Notifications"], summary="Notification dropdown feed")
async def notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(30).all()


@app.post("/api/notifications/{notification_id}/read", response_model=NotificationOut, tags=["Notifications"], summary="Mark notification as read")
async def mark_notification_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@app.get("/api/reports/{dataset_id}/summary", response_model=ReportSummary, tags=["Reports"], summary="Report summary data")
async def report_summary(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = get_user_dataset(db, dataset_id, current_user)
    latest_run = db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset_id).order_by(ForecastRun.created_at.desc()).first()
    metrics = db.query(ModelMetric).filter(ModelMetric.run_id == latest_run.id).all() if latest_run else []
    return {"dataset": dataset, "latest_run": latest_run, "metrics": metrics, "forecast": forecast_points(latest_run) if latest_run else []}


@app.get("/api/reports/{dataset_id}/excel", tags=["Reports"], summary="Export enterprise Excel report")
async def export_excel(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = get_user_dataset(db, dataset_id, current_user)
    output = build_excel_report(db, dataset)
    notify(db, current_user.id, "Excel report generated", f"{dataset.name} Excel report is ready.", "success")
    log_activity(db, current_user.id, "report.excel.generated", "dataset", dataset.id)
    db.commit()
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={dataset.name}-enterprise-report.xlsx"})


@app.get("/api/reports/{dataset_id}/pdf", tags=["Reports"], summary="Export branded PDF report")
async def export_pdf(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = get_user_dataset(db, dataset_id, current_user)
    output = build_pdf_report(db, dataset)
    notify(db, current_user.id, "PDF report generated", f"{dataset.name} PDF report is ready.", "success")
    log_activity(db, current_user.id, "report.pdf.generated", "dataset", dataset.id)
    db.commit()
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={dataset.name}-enterprise-report.pdf"})


@app.get("/api/reports/{dataset_id}/comparison/excel", tags=["Reports"], summary="Export forecasting comparison report")
async def export_comparison(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = get_user_dataset(db, dataset_id, current_user)
    comparisons = compare_models(db, dataset.id)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        pd.DataFrame([{key: item[key] for key in ["model_name", "average_rmse", "average_mae", "average_accuracy", "confidence_score"]} for item in comparisons]).to_excel(writer, sheet_name="Model Comparison", index=False)
        pd.DataFrame(advanced_analytics_payload(db, dataset.id)["inventory_risk"]).to_excel(writer, sheet_name="Inventory Risk", index=False)
    output.seek(0)
    log_activity(db, current_user.id, "report.comparison.generated", "dataset", dataset.id)
    db.commit()
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={dataset.name}-model-comparison.xlsx"})


@app.get("/api/admin/summary", response_model=AdminSummary, tags=["Admin"], summary="Enterprise admin dashboard")
async def admin_summary(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    recent = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(10).all()
    usage = db.query(ForecastRun.model_name, func.count(ForecastRun.id)).group_by(ForecastRun.model_name).all()
    return {
        "total_users": db.query(User).count(),
        "total_datasets": db.query(Dataset).count(),
        "total_records": db.query(SalesRecord).count(),
        "total_forecast_runs": db.query(ForecastRun).count(),
        "total_reports": db.query(ActivityLog).filter(ActivityLog.action.like("report.%")).count(),
        "active_users": db.query(User).filter(User.is_active.is_(True)).count(),
        "recent_activity": [{"action": item.action, "entity_type": item.entity_type, "entity_id": item.entity_id, "created_at": item.created_at} for item in recent],
        "model_usage": [{"model_name": name, "count": count} for name, count in usage],
    }


@app.get("/api/admin/users", response_model=List[UserOut], tags=["Admin"], summary="List users")
async def admin_users(search: str = "", role: str = "", _: User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(User)
    if search:
        query = query.filter((User.name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")))
    if role:
        query = query.filter(User.role == role)
    return query.order_by(User.created_at.desc()).all()


@app.patch("/api/admin/users/{user_id}/role", response_model=UserOut, tags=["Admin"], summary="Assign user role")
async def update_user_role(user_id: int, payload: RoleUpdateIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id and payload.role != "super_admin":
        raise HTTPException(status_code=400, detail="Super Admin cannot remove their own permission")
    user.role = payload.role
    log_activity(db, current_user.id, "user.role.updated", "user", user.id, {"role": payload.role})
    db.commit()
    db.refresh(user)
    return user


@app.get("/api/admin/datasets", tags=["Admin"], summary="Admin dataset inventory")
async def admin_datasets(page: int = 1, page_size: int = 20, search: str = "", _: User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(Dataset, User).join(User, Dataset.owner_id == User.id)
    if search:
        query = query.filter(Dataset.name.ilike(f"%{search}%"))
    total = query.count()
    rows = query.order_by(Dataset.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [{"id": dataset.id, "name": dataset.name, "row_count": dataset.row_count, "status": dataset.status, "owner": user.email, "created_at": dataset.created_at} for dataset, user in rows], "total": total, "page": page, "page_size": page_size}
    MonitoringOut,
    detect_anomalies,


@app.get("/api/profile", response_model=UserProfileOut, tags=["Authentication"], summary="Extended user profile")
async def profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile_row = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile_row:
        profile_row = UserProfile(user_id=current_user.id)
        db.add(profile_row)
        db.commit()
        db.refresh(profile_row)
    return {"user": current_user, "title": profile_row.title, "department": profile_row.department, "phone": profile_row.phone, "preferences": __import__("json").loads(profile_row.preferences_json or "{}")}


@app.patch("/api/profile", response_model=UserProfileOut, tags=["Authentication"], summary="Update user profile")
async def update_profile(payload: ProfileUpdateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile_row = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first() or UserProfile(user_id=current_user.id)
    if payload.name:
        current_user.name = payload.name
    profile_row.title = payload.title
    profile_row.department = payload.department
    profile_row.phone = payload.phone
    profile_row.preferences_json = __import__("json").dumps(payload.preferences)
    db.add(profile_row)
    log_activity(db, current_user.id, "user.profile.updated", "user", current_user.id)
    db.commit()
    db.refresh(profile_row)
    return {"user": current_user, "title": profile_row.title, "department": profile_row.department, "phone": profile_row.phone, "preferences": payload.preferences}


@app.post("/api/auth/password-reset/request", tags=["Authentication"], summary="Create password reset token")
async def request_password_reset(payload: PasswordResetRequestIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        token = __import__("secrets").token_urlsafe(24)
        db.add(PasswordResetToken(user_id=user.id, token=token, expires_at=datetime.utcnow() + timedelta(hours=2)))
        notify(db, user.id, "Password reset requested", f"Use reset token: {token}", "info")
        log_activity(db, user.id, "user.password_reset.requested", "user", user.id)
        db.commit()
    return {"success": True, "message": "If the email exists, a reset token was generated."}


@app.post("/api/auth/password-reset/confirm", tags=["Authentication"], summary="Reset password with token")
async def confirm_password_reset(payload: PasswordResetConfirmIn, db: Session = Depends(get_db)):
    reset = db.query(PasswordResetToken).filter(PasswordResetToken.token == payload.token, PasswordResetToken.used_at.is_(None), PasswordResetToken.expires_at >= datetime.utcnow()).first()
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user = db.query(User).filter(User.id == reset.user_id).first()
    user.hashed_password = hash_password(payload.new_password)
    reset.used_at = datetime.utcnow()
    log_activity(db, user.id, "user.password_reset.completed", "user", user.id)
    db.commit()
    return {"success": True}


@app.get("/api/automation/schedules", response_model=List[ForecastScheduleOut], tags=["Automation"], summary="List automated forecast schedules")
async def list_schedules(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(ForecastSchedule)
    if current_user.role not in {"admin", "super_admin"}:
        query = query.filter(ForecastSchedule.created_by == current_user.id)
    return query.order_by(ForecastSchedule.created_at.desc()).all()


@app.post("/api/automation/schedules", response_model=ForecastScheduleOut, tags=["Automation"], summary="Create recurring forecast schedule")
async def create_schedule(payload: ForecastScheduleIn, current_user: User = Depends(require_analyst), db: Session = Depends(get_db)):
    get_user_dataset(db, payload.dataset_id, current_user)
    schedule = ForecastSchedule(**payload.model_dump(), created_by=current_user.id, next_run_at=datetime.utcnow() + timedelta(minutes=payload.interval_minutes))
    db.add(schedule)
    log_activity(db, current_user.id, "automation.schedule.created", "dataset", payload.dataset_id, {"interval_minutes": payload.interval_minutes})
    db.commit()
    db.refresh(schedule)
    return schedule


@app.post("/api/automation/run-due", tags=["Automation"], summary="Execute due automated forecasts")
async def run_due_schedules(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    executed = run_due_forecast_schedules(db)
    db.commit()
    return {"executed": executed, "count": len(executed)}


@app.get("/api/integrations", response_model=List[IntegrationOut], tags=["Integrations"], summary="List enterprise integrations")
async def list_integrations(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(Integration).order_by(Integration.created_at.desc()).all()
    return [{"id": row.id, "name": row.name, "provider": row.provider, "base_url": row.base_url, "auth_type": row.auth_type, "status": row.status, "settings": __import__("json").loads(row.settings_json or "{}"), "created_at": row.created_at} for row in rows]


@app.post("/api/integrations", response_model=IntegrationOut, tags=["Integrations"], summary="Create ERP, inventory, or external API integration")
async def create_integration(payload: IntegrationIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = Integration(name=payload.name, provider=payload.provider, base_url=payload.base_url, auth_type=payload.auth_type, secret_ref=payload.secret_ref, status="active", settings_json=__import__("json").dumps(payload.settings), created_by=current_user.id)
    db.add(row)
    log_activity(db, current_user.id, "integration.created", "integration", None, {"provider": payload.provider})
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "provider": row.provider, "base_url": row.base_url, "auth_type": row.auth_type, "status": row.status, "settings": payload.settings, "created_at": row.created_at}


@app.post("/api/integrations/{integration_id}/test", tags=["Integrations"], summary="Validate integration configuration")
async def test_integration(integration_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(Integration).filter(Integration.id == integration_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")
    row.status = "verified" if row.base_url else "needs_configuration"
    log_activity(db, current_user.id, "integration.tested", "integration", integration_id, {"status": row.status})
    db.commit()
    return {"success": row.status == "verified", "status": row.status, "message": "Configuration accepted for managed connector."}


@app.get("/api/webhooks", response_model=List[WebhookOut], tags=["Integrations"], summary="List real-time webhook subscriptions")
async def list_webhooks(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(WebhookSubscription).order_by(WebhookSubscription.created_at.desc()).all()


@app.post("/api/webhooks", response_model=WebhookOut, tags=["Integrations"], summary="Create webhook subscription")
async def create_webhook(payload: WebhookIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = WebhookSubscription(**payload.model_dump(), created_by=current_user.id)
    db.add(row)
    log_activity(db, current_user.id, "webhook.created", "webhook", None, {"event_type": payload.event_type})
    db.commit()
    db.refresh(row)
    return row


@app.get("/api/ai/{dataset_id}/enterprise-insights", response_model=EnterpriseInsightsOut, tags=["Optimization"], summary="Product recommendations, customer behavior, spikes, and inventory optimization")
async def enterprise_insights(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    return enterprise_ai_insights(db, dataset_id)


@app.get("/api/forecast/{dataset_id}/insights", response_model=ForecastTrendOut, tags=["Forecasting"], summary="Accuracy trends, confidence history, and business recommendations")
async def forecast_insights(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    return forecast_trend_payload(db, dataset_id)


@app.get("/api/dashboard/widgets", response_model=List[DashboardWidgetOut], tags=["Analytics"], summary="User dashboard widgets")
async def dashboard_widgets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    create_default_widgets(db, current_user.id)
    db.commit()
    rows = db.query(DashboardWidget).filter(DashboardWidget.user_id == current_user.id).order_by(DashboardWidget.position).all()
    return [{"id": row.id, "user_id": row.user_id, "widget_key": row.widget_key, "title": row.title, "position": row.position, "is_visible": row.is_visible, "settings": __import__("json").loads(row.settings_json or "{}")} for row in rows]


@app.post("/api/dashboard/widgets", response_model=DashboardWidgetOut, tags=["Analytics"], summary="Create or update dashboard widget")
async def upsert_dashboard_widget(payload: DashboardWidgetIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(DashboardWidget).filter(DashboardWidget.user_id == current_user.id, DashboardWidget.widget_key == payload.widget_key).first()
    if not row:
        row = DashboardWidget(user_id=current_user.id, widget_key=payload.widget_key)
    row.title = payload.title
    row.position = payload.position
    row.is_visible = payload.is_visible
    row.settings_json = __import__("json").dumps(payload.settings)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "user_id": row.user_id, "widget_key": row.widget_key, "title": row.title, "position": row.position, "is_visible": row.is_visible, "settings": payload.settings}


@app.get("/api/dashboard/{dataset_id}/summary", response_model=DashboardSummaryOut, tags=["Analytics"], summary="Downloadable dashboard summary payload")
async def dashboard_summary(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    analytics_data = analytics_payload(db, dataset_id, None, None, "", "")
    advanced = advanced_analytics_payload(db, dataset_id)
    return {"dataset_id": dataset_id, "generated_at": datetime.utcnow(), "kpis": {"total_sales": analytics_data["total_sales"], "total_units": analytics_data["total_units"], "accuracy": analytics_data["forecast_accuracy"], "confidence": analytics_data["confidence_score"]}, "insights": advanced["generated_insights"]}


@app.get("/api/dashboard/{dataset_id}/summary.csv", tags=["Analytics"], summary="Download dashboard summary CSV")
async def dashboard_summary_csv(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    summary = await dashboard_summary(dataset_id, current_user, db)
    output = BytesIO()
    pd.DataFrame([summary["kpis"]]).to_csv(output, index=False)
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=dashboard-summary.csv"})


@app.get("/api/alerts/rules", response_model=List[AlertRuleOut], tags=["Notifications"], summary="List configurable alert rules")
async def list_alert_rules(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(AlertRule).filter(AlertRule.user_id == current_user.id).order_by(AlertRule.created_at.desc()).all()


@app.post("/api/alerts/rules", response_model=AlertRuleOut, tags=["Notifications"], summary="Create threshold-based alert rule")
async def create_alert_rule(payload: AlertRuleIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.dataset_id:
        get_user_dataset(db, payload.dataset_id, current_user)
    row = AlertRule(**payload.model_dump(), user_id=current_user.id)
    db.add(row)
    log_activity(db, current_user.id, "alert.rule.created", "alert", None, {"metric": payload.metric, "threshold": payload.threshold})
    db.commit()
    db.refresh(row)
    return row


@app.post("/api/alerts/evaluate/{dataset_id}", tags=["Notifications"], summary="Evaluate alert rules for a dataset")
async def evaluate_alerts(dataset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_user_dataset(db, dataset_id, current_user)
    triggered = evaluate_alert_rules(db, current_user.id, dataset_id)
    db.commit()
    return {"triggered": len(triggered)}


@app.patch("/api/admin/users/{user_id}/status", response_model=UserOut, tags=["Admin"], summary="Enable or disable user account")
async def update_user_status(user_id: int, is_active: bool, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id and not is_active:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    user.is_active = is_active
    log_activity(db, current_user.id, "user.status.updated", "user", user.id, {"is_active": is_active})
    db.commit()
    db.refresh(user)
    return user
