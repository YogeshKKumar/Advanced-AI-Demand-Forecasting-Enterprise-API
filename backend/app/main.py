from __future__ import annotations

from io import BytesIO
from datetime import datetime, timedelta
from math import ceil
from time import perf_counter
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
from .models import ApiMetric, ActivityLog, Dataset, ForecastRun, ModelMetric, Notification, RetrainingJob, SalesRecord, User
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
    if current_user.role != "admin":
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
