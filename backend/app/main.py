from __future__ import annotations

from io import BytesIO
from math import ceil
from typing import List, Optional

import pandas as pd
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, hash_password, require_admin, verify_password
from .database import Base, engine, get_db
from .models import ActivityLog, Dataset, ForecastRun, ModelMetric, Notification, SalesRecord, User
from .schemas import (
    ActivityOut,
    AdminSummary,
    AnalyticsOut,
    DatasetOut,
    DatasetUploadResponse,
    ForecastRequest,
    ForecastResponse,
    ForecastRunOut,
    ModelComparisonItem,
    NotificationOut,
    PaginatedDatasets,
    ReportSummary,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
)
from .services import (
    SUPPORTED_MODELS,
    analytics_payload,
    build_excel_report,
    build_pdf_report,
    compare_models,
    forecast_points,
    get_user_dataset,
    log_activity,
    normalize_dataset,
    notify,
    train_and_forecast,
)
from .settings import settings


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Modern enterprise-level full-stack AI forecasting API with JWT security, role-based access, "
        "Linear Regression, Random Forest, XGBoost, Prophet, model comparison, analytics, activity logs, "
        "notifications, admin APIs, Excel/PDF exports, and detailed Swagger examples. Developed by Yogeshwaran K.\n\n"
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
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    description="Creates an analyst account. The first registered user is automatically assigned the admin role.",
    responses={200: {"description": "JWT token and user profile returned after registration"}},
)
async def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    role = "admin" if db.query(User).count() == 0 else "analyst"
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
    if current_user.role != "admin":
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
    current_user: User = Depends(get_current_user),
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
async def forecast(dataset_id: int, payload: ForecastRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = get_user_dataset(db, dataset_id, current_user)
    run = train_and_forecast(db, dataset.id, payload.periods, payload.model_name)
    notify(db, current_user.id, "Forecast completed", f"{dataset.name} generated {run.total_predictions} predictions using {run.model_name}.", "success")
    log_activity(db, current_user.id, "forecast.completed", "dataset", dataset.id, {"model": run.model_name, "accuracy": run.accuracy, "confidence": run.confidence_score})
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
    return analytics_payload(db, dataset_id, start_date, end_date, category, region)


@app.get("/api/activity", response_model=List[ActivityOut], tags=["Analytics"], summary="Recent activity logs")
async def activities(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(ActivityLog)
    if current_user.role != "admin":
        query = query.filter(ActivityLog.user_id == current_user.id)
    items = query.order_by(ActivityLog.created_at.desc()).limit(40).all()
    return [{"id": item.id, "action": item.action, "entity_type": item.entity_type, "entity_id": item.entity_id, "metadata": __import__("json").loads(item.metadata_json), "created_at": item.created_at} for item in items]


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
async def admin_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@app.get("/api/admin/datasets", tags=["Admin"], summary="Admin dataset inventory")
async def admin_datasets(page: int = 1, page_size: int = 20, search: str = "", _: User = Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(Dataset, User).join(User, Dataset.owner_id == User.id)
    if search:
        query = query.filter(Dataset.name.ilike(f"%{search}%"))
    total = query.count()
    rows = query.order_by(Dataset.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [{"id": dataset.id, "name": dataset.name, "row_count": dataset.row_count, "status": dataset.status, "owner": user.email, "created_at": dataset.created_at} for dataset, user in rows], "total": total, "page": page, "page_size": page_size}
