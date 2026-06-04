from __future__ import annotations

from io import BytesIO
from math import ceil
from typing import List

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import settings
from .contracts import (
    AdminOut,
    AlertOut,
    AuthOut,
    CompareOut,
    InsightOut,
    ScenarioIn,
    ScenarioResult,
    SigninIn,
    SignupIn,
    WorkbookPage,
    UploadOut,
)
from .db import Base, engine, session_scope
from .engine import audit, alert, compare_algorithms, excel_report, insight_pack, pdf_report, prepare_table, projection_rows, run_scenario
from .entities import Account, Alert, AuditEvent, DemandObservation, DemandWorkbook, PlanningScenario
from .security import admin_account, check_secret, current_account, hash_secret, issue_token

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.product_name,
    version=settings.version,
    description=(
        "Green and white corporate forecasting enhancement platform for Priya. "
        "Includes secured workbook uploads, demand scenarios, algorithm comparison, "
        "business insights, alerts, admin summaries, and Excel/PDF exports.\n\n"
        "Swagger authorization format: `Bearer <access_token>`"
    ),
    openapi_tags=[
        {"name": "Session", "description": "Signup, signin, and profile authorization."},
        {"name": "Workbooks", "description": "Demand workbook upload and inventory."},
        {"name": "Planning", "description": "Forecast scenarios and algorithm comparison."},
        {"name": "Insights", "description": "Corporate analytics dashboard APIs."},
        {"name": "Exports", "description": "Excel and PDF business reports."},
        {"name": "Admin", "description": "Admin workspace for Priya's platform."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def owned_workbook(db: Session, workbook_id: int, account: Account) -> DemandWorkbook:
    query = db.query(DemandWorkbook).filter(DemandWorkbook.id == workbook_id)
    if account.role != "admin":
        query = query.filter(DemandWorkbook.owner_id == account.id)
    workbook = query.first()
    if not workbook:
        raise HTTPException(status_code=404, detail="Workbook not found")
    return workbook


@app.get("/api/v1/health", tags=["System"])
async def health():
    return {"status": "ready", "project": settings.product_name, "owner": "Priya"}


@app.post("/api/v1/session/signup", response_model=AuthOut, tags=["Session"])
async def signup(payload: SignupIn, db: Session = Depends(session_scope)):
    if db.query(Account).filter(Account.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already exists")
    role = "admin" if db.query(Account).count() == 0 else "planner"
    account = Account(full_name=payload.full_name, email=payload.email, password_hash=hash_secret(payload.password), role=role)
    db.add(account)
    db.flush()
    alert(db, account.id, "Workspace ready", "Your forecasting enhancement workspace has been configured.", "success")
    audit(db, account.id, "account.signup", "account", {"role": role})
    db.commit()
    db.refresh(account)
    return {"access_token": issue_token(account.email, account.role), "account": account}


@app.post("/api/v1/session/signin", response_model=AuthOut, tags=["Session"])
async def signin(payload: SigninIn, db: Session = Depends(session_scope)):
    account = db.query(Account).filter(Account.email == payload.email).first()
    if not account or not check_secret(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    audit(db, account.id, "account.signin", "account")
    db.commit()
    return {"access_token": issue_token(account.email, account.role), "account": account}


@app.get("/api/v1/session/me", tags=["Session"])
async def me(account: Account = Depends(current_account)):
    return account


@app.get("/api/v1/workbooks", response_model=WorkbookPage, tags=["Workbooks"])
async def workbooks(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    q: str = "",
    state: str = "",
    account: Account = Depends(current_account),
    db: Session = Depends(session_scope),
):
    query = db.query(DemandWorkbook)
    if account.role != "admin":
        query = query.filter(DemandWorkbook.owner_id == account.id)
    if q:
        query = query.filter(DemandWorkbook.title.ilike(f"%{q}%"))
    if state:
        query = query.filter(DemandWorkbook.state == state)
    total = query.count()
    rows = query.order_by(DemandWorkbook.uploaded_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"records": rows, "total": total, "page": page, "size": size, "pages": ceil(total / size) if total else 0}


@app.post("/api/v1/workbooks/import", response_model=UploadOut, tags=["Workbooks"])
async def import_workbook(file: UploadFile = File(...), account: Account = Depends(current_account), db: Session = Depends(session_scope)):
    content = await file.read()
    try:
        if file.filename and file.filename.lower().endswith(".csv"):
            frame = pd.read_csv(BytesIO(content))
        elif file.filename and file.filename.lower().endswith((".xlsx", ".xls")):
            frame = pd.read_excel(BytesIO(content))
        else:
            raise ValueError("Upload CSV or Excel only")
        clean, profile = prepare_table(frame)
    except Exception as exc:
        alert(db, account.id, "Import failed", str(exc), "error")
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    workbook = DemandWorkbook(owner_id=account.id, title=file.filename or "demand-workbook", rows_loaded=len(clean))
    db.add(workbook)
    db.flush()
    db.bulk_save_objects([
        DemandObservation(
            workbook_id=workbook.id,
            period_date=row.date.date(),
            item_name=row.item_name,
            segment=row.category,
            market=row.region,
            units=float(row.units),
            revenue=float(row.revenue),
        )
        for row in clean.itertuples(index=False)
    ])
    alert(db, account.id, "Workbook imported", f"{workbook.title} loaded with {workbook.rows_loaded} accepted rows.", "success")
    audit(db, account.id, "workbook.imported", str(workbook.id), profile)
    db.commit()
    db.refresh(workbook)
    return {"workbook": workbook, "profile": profile}


@app.get("/api/v1/workbooks/{workbook_id}/dimensions", tags=["Workbooks"])
async def dimensions(workbook_id: int, account: Account = Depends(current_account), db: Session = Depends(session_scope)):
    owned_workbook(db, workbook_id, account)
    base = db.query(DemandObservation).filter(DemandObservation.workbook_id == workbook_id)
    return {
        "items": [row[0] for row in base.with_entities(DemandObservation.item_name).distinct().all()],
        "segments": [row[0] for row in base.with_entities(DemandObservation.segment).distinct().all()],
        "markets": [row[0] for row in base.with_entities(DemandObservation.market).distinct().all()],
    }


@app.get("/api/v1/planning/algorithms", tags=["Planning"])
async def algorithms():
    return {"records": [{"id": item, "name": item.replace("_", " ").title()} for item in ["linear", "ridge", "forest", "seasonal_average"]]}


@app.post("/api/v1/planning/{workbook_id}/scenario", response_model=ScenarioResult, tags=["Planning"])
async def create_scenario(workbook_id: int, payload: ScenarioIn, account: Account = Depends(current_account), db: Session = Depends(session_scope)):
    workbook = owned_workbook(db, workbook_id, account)
    try:
        scenario = run_scenario(db, workbook.id, payload.algorithm, payload.horizon)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    alert(db, account.id, "Scenario completed", f"{payload.algorithm} scenario completed for {workbook.title}.", "success")
    audit(db, account.id, "scenario.completed", str(workbook.id), {"algorithm": payload.algorithm, "quality": scenario.quality_score})
    db.commit()
    db.refresh(scenario)
    return {"scenario": scenario, "projections": projection_rows(scenario)}


@app.get("/api/v1/planning/{workbook_id}/compare", response_model=List[CompareOut], tags=["Planning"])
async def compare(workbook_id: int, account: Account = Depends(current_account), db: Session = Depends(session_scope)):
    owned_workbook(db, workbook_id, account)
    rows = compare_algorithms(db, workbook_id)
    audit(db, account.id, "scenario.compared", str(workbook_id))
    db.commit()
    return rows


@app.get("/api/v1/insights/{workbook_id}", response_model=InsightOut, tags=["Insights"])
async def insights(workbook_id: int, account: Account = Depends(current_account), db: Session = Depends(session_scope)):
    owned_workbook(db, workbook_id, account)
    return insight_pack(db, workbook_id)


@app.get("/api/v1/alerts", response_model=List[AlertOut], tags=["Insights"])
async def alerts(account: Account = Depends(current_account), db: Session = Depends(session_scope)):
    return db.query(Alert).filter(Alert.account_id == account.id).order_by(Alert.created_at.desc()).limit(30).all()


@app.post("/api/v1/alerts/{alert_id}/seen", response_model=AlertOut, tags=["Insights"])
async def seen(alert_id: int, account: Account = Depends(current_account), db: Session = Depends(session_scope)):
    item = db.query(Alert).filter(Alert.id == alert_id, Alert.account_id == account.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Alert not found")
    item.seen = True
    db.commit()
    db.refresh(item)
    return item


@app.get("/api/v1/exports/{workbook_id}/xlsx", tags=["Exports"])
async def export_xlsx(workbook_id: int, account: Account = Depends(current_account), db: Session = Depends(session_scope)):
    workbook = owned_workbook(db, workbook_id, account)
    audit(db, account.id, "export.xlsx", str(workbook_id))
    db.commit()
    return StreamingResponse(excel_report(db, workbook.id), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={workbook.title}-enhancement.xlsx"})


@app.get("/api/v1/exports/{workbook_id}/pdf", tags=["Exports"])
async def export_pdf(workbook_id: int, account: Account = Depends(current_account), db: Session = Depends(session_scope)):
    workbook = owned_workbook(db, workbook_id, account)
    audit(db, account.id, "export.pdf", str(workbook_id))
    db.commit()
    return StreamingResponse(pdf_report(db, workbook), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={workbook.title}-enhancement.pdf"})


@app.get("/api/v1/admin/overview", response_model=AdminOut, tags=["Admin"])
async def admin_overview(_: Account = Depends(admin_account), db: Session = Depends(session_scope)):
    events = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(10).all()
    return {
        "accounts": db.query(Account).count(),
        "workbooks": db.query(DemandWorkbook).count(),
        "observations": db.query(DemandObservation).count(),
        "scenarios": db.query(PlanningScenario).count(),
        "alerts": db.query(Alert).count(),
        "recent_events": [{"event_name": row.event_name, "reference": row.reference, "created_at": row.created_at} for row in events],
    }
