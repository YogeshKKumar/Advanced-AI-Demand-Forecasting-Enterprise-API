from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import ActivityLog, AlertRule, DashboardLayout, DashboardWidget, Dataset, DatasetVersion, ExecutiveReportSchedule, ForecastComment, ForecastProject, ForecastResult, ForecastRevision, ForecastRun, ForecastScenario, ForecastScenarioResult, ForecastSchedule, Integration, ModelMetric, Notification, PasswordResetToken, ProjectActivity, ProjectDataset, ProjectMember, ReportJob, ReportShare, RetrainingJob, SalesRecord, User, UserProfile, WebhookSubscription

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

try:
    from xgboost import XGBRegressor
except Exception:
    XGBRegressor = None

try:
    from prophet import Prophet
except Exception:
    Prophet = None


SUPPORTED_MODELS = ["linear_regression", "random_forest", "xgboost", "prophet", "ensemble"]
REQUIRED_COLUMNS = {"date", "product", "quantity", "sales"}
OPTIONAL_COLUMNS = {"category", "region"}


def log_activity(db: Session, user_id: Optional[int], action: str, entity_type: str = "system", entity_id: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
    db.add(ActivityLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, metadata_json=json.dumps(metadata or {})))


def notify(db: Session, user_id: int, title: str, message: str, type_: str = "info") -> Notification:
    notification = Notification(user_id=user_id, title=title, message=message, type=type_)
    db.add(notification)
    return notification


def normalize_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    df = df.copy()
    df.columns = [str(column).strip().lower() for column in df.columns]
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    before_rows = len(df)
    selected = list(REQUIRED_COLUMNS | (OPTIONAL_COLUMNS & set(df.columns)))
    df = df[selected]
    df["category"] = df.get("category", "General")
    df["region"] = df.get("region", "All Regions")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["product"] = df["product"].astype(str).str.strip()
    df["category"] = df["category"].fillna("General").astype(str).str.strip().replace("", "General")
    df["region"] = df["region"].fillna("All Regions").astype(str).str.strip().replace("", "All Regions")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce")
    df = df.dropna(subset=["date", "product", "quantity", "sales"])
    df = df[df["product"] != ""].drop_duplicates(subset=["date", "product", "region"]).sort_values("date")
    return df, {
        "original_rows": before_rows,
        "clean_rows": len(df),
        "removed_rows": before_rows - len(df),
        "products": int(df["product"].nunique()) if not df.empty else 0,
        "categories": int(df["category"].nunique()) if not df.empty else 0,
        "regions": int(df["region"].nunique()) if not df.empty else 0,
    }


def get_user_dataset(db: Session, dataset_id: int, user: User) -> Dataset:
    query = db.query(Dataset).filter(Dataset.id == dataset_id)
    if user.role not in {"admin", "super_admin"}:
        query = query.filter(Dataset.owner_id == user.id)
    dataset = query.first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
    if len(actual) == 0:
        return {"rmse": 0, "mae": 0, "accuracy": 100, "confidence_score": 95}
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    mae = float(mean_absolute_error(actual, predicted))
    mean_actual = max(float(np.mean(np.abs(actual))), 1.0)
    accuracy = max(0, min(100, 100 - ((mae / mean_actual) * 100)))
    confidence = max(40, min(99, accuracy - min(15, rmse / mean_actual * 10) + 4))
    return {"rmse": round(rmse, 2), "mae": round(mae, 2), "accuracy": round(accuracy, 2), "confidence_score": round(confidence, 2)}


def _fit_predict(monthly: pd.DataFrame, model_name: str, periods: int) -> Tuple[List[float], Dict[str, float]]:
    monthly = monthly.copy().sort_values("date")
    monthly["step"] = np.arange(len(monthly))
    if len(monthly) < 3:
        baseline = float(monthly["quantity"].mean()) if len(monthly) else 0
        return [round(baseline, 2)] * periods, {"rmse": 0, "mae": 0, "accuracy": 88, "confidence_score": 82}
    split_at = max(2, int(len(monthly) * 0.8))
    train, test = monthly.iloc[:split_at], monthly.iloc[split_at:]
    future_steps = np.arange(len(monthly), len(monthly) + periods).reshape(-1, 1)

    if model_name == "ensemble":
        member_results = [_fit_predict(monthly, member, periods) for member in ["linear_regression", "random_forest", "xgboost"]]
        futures = np.array([result[0] for result in member_results])
        future = np.mean(futures, axis=0).tolist()
        member_scores = [result[1] for result in member_results]
        score = {
            metric: round(float(np.mean([item[metric] for item in member_scores])), 2)
            for metric in ["rmse", "mae", "accuracy", "confidence_score"]
        }
        score["confidence_score"] = min(99, round(score["confidence_score"] + 2, 2))
        return [max(0, round(float(value), 2)) for value in future], score

    if model_name == "prophet" and Prophet is not None:
        prophet_train = train.rename(columns={"date": "ds", "quantity": "y"})[["ds", "y"]]
        model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        model.fit(prophet_train)
        test_frame = pd.DataFrame({"ds": test["date"]})
        pred = model.predict(test_frame)["yhat"].to_numpy() if len(test) else np.array([])
        future = model.predict(pd.DataFrame({"ds": pd.date_range(monthly["date"].max() + pd.DateOffset(months=1), periods=periods, freq="MS")}))["yhat"].to_list()
        return [max(0, round(float(value), 2)) for value in future], _metrics(test["quantity"].to_numpy(), pred)

    if model_name == "random_forest":
        model = RandomForestRegressor(n_estimators=180, random_state=42, min_samples_leaf=1)
    elif model_name == "xgboost" and XGBRegressor is not None:
        model = XGBRegressor(n_estimators=140, learning_rate=0.08, max_depth=3, random_state=42, objective="reg:squarederror")
    else:
        model = LinearRegression()

    model.fit(train[["step"]], train["quantity"])
    pred = model.predict(test[["step"]]) if len(test) else np.array([])
    score = _metrics(test["quantity"].to_numpy(), pred)
    model.fit(monthly[["step"]], monthly["quantity"])
    future = model.predict(future_steps)
    return [max(0, round(float(value), 2)) for value in future], score


def compare_models(db: Session, dataset_id: int) -> List[Dict[str, Any]]:
    rows = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id).all()
    df = pd.DataFrame([{"date": row.date, "product": row.product, "quantity": row.quantity} for row in rows])
    if df.empty:
        return []
    df["date"] = pd.to_datetime(df["date"])
    comparisons = []
    for model_name in SUPPORTED_MODELS:
        product_scores = []
        for product, product_df in df.groupby("product"):
            monthly = product_df.set_index("date")["quantity"].resample("MS").sum().reset_index()
            _, score = _fit_predict(monthly, model_name, 3)
            product_scores.append({"product": product, **score})
        comparisons.append({
            "model_name": model_name,
            "average_rmse": round(float(np.mean([item["rmse"] for item in product_scores])), 2),
            "average_mae": round(float(np.mean([item["mae"] for item in product_scores])), 2),
            "average_accuracy": round(float(np.mean([item["accuracy"] for item in product_scores])), 2),
            "confidence_score": round(float(np.mean([item["confidence_score"] for item in product_scores])), 2),
            "products": product_scores,
        })
    return sorted(comparisons, key=lambda item: item["average_accuracy"], reverse=True)


def train_and_forecast(db: Session, dataset_id: int, periods: int, model_name: str) -> ForecastRun:
    if model_name not in SUPPORTED_MODELS:
        raise HTTPException(status_code=422, detail=f"Unsupported model. Choose one of: {', '.join(SUPPORTED_MODELS)}")
    rows = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id).order_by(SalesRecord.date).all()
    df = pd.DataFrame([{"date": row.date, "product": row.product, "quantity": row.quantity} for row in rows])
    if df.empty:
        raise HTTPException(status_code=400, detail="Dataset has no records")
    df["date"] = pd.to_datetime(df["date"])
    run = ForecastRun(dataset_id=dataset_id, model_name=model_name, periods=periods, status="completed")
    db.add(run)
    db.flush()
    aggregate = []
    prediction_count = 0
    for product, product_df in df.groupby("product"):
        monthly = product_df.set_index("date")["quantity"].resample("MS").sum().reset_index()
        predictions, score = _fit_predict(monthly, model_name, periods)
        aggregate.append(score)
        db.add(ModelMetric(run_id=run.id, model_name=model_name, product=product, **score))
        last_date = monthly["date"].max()
        for index, predicted in enumerate(predictions, start=1):
            spread = max(predicted * (1 - score["confidence_score"] / 100), 1)
            db.add(ForecastResult(
                dataset_id=dataset_id,
                run_id=run.id,
                product=product,
                model_name=model_name,
                forecast_date=(last_date + pd.DateOffset(months=index)).date(),
                predicted_demand=predicted,
                lower_bound=max(0, round(predicted - spread, 2)),
                upper_bound=round(predicted + spread, 2),
                accuracy=score["accuracy"],
                confidence_score=score["confidence_score"],
            ))
            prediction_count += 1
    run.rmse = round(float(np.mean([item["rmse"] for item in aggregate])), 2)
    run.mae = round(float(np.mean([item["mae"] for item in aggregate])), 2)
    run.accuracy = round(float(np.mean([item["accuracy"] for item in aggregate])), 2)
    run.confidence_score = round(float(np.mean([item["confidence_score"] for item in aggregate])), 2)
    run.total_predictions = prediction_count
    db.flush()
    return run


def forecast_points(run: ForecastRun) -> List[Dict[str, Any]]:
    return [{
        "date": item.forecast_date,
        "product": item.product,
        "predicted_demand": item.predicted_demand,
        "lower_bound": item.lower_bound,
        "upper_bound": item.upper_bound,
        "accuracy": item.accuracy,
        "confidence_score": item.confidence_score,
        "model_name": item.model_name,
    } for item in run.results]


def analytics_payload(db: Session, dataset_id: int, start_date: Optional[str], end_date: Optional[str], category: str, region: str) -> Dict[str, Any]:
    query = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id)
    if start_date:
        query = query.filter(SalesRecord.date >= start_date)
    if end_date:
        query = query.filter(SalesRecord.date <= end_date)
    if category:
        query = query.filter(SalesRecord.category == category)
    if region:
        query = query.filter(SalesRecord.region == region)
    rows = query.order_by(SalesRecord.date).all()
    df = pd.DataFrame([{"date": r.date, "product": r.product, "category": r.category, "region": r.region, "quantity": r.quantity, "sales": r.sales} for r in rows])
    latest_run = db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset_id).order_by(ForecastRun.created_at.desc()).first()
    if df.empty:
        return {"total_sales": 0, "total_units": 0, "average_order_value": 0, "monthly_sales": [], "top_products": [], "sales_by_category": [], "sales_by_region": [], "forecast_accuracy": 0, "confidence_score": 0, "forecast": [], "recent_activity": [], "filters": {}}
    df["date"] = pd.to_datetime(df["date"])
    monthly = df.set_index("date")["sales"].resample("MS").sum().reset_index()
    monthly["month"] = monthly["date"].dt.strftime("%b %Y")
    activity = db.query(ActivityLog).filter(ActivityLog.entity_id == dataset_id).order_by(ActivityLog.created_at.desc()).limit(8).all()
    return {
        "total_sales": round(float(df["sales"].sum()), 2),
        "total_units": round(float(df["quantity"].sum()), 2),
        "average_order_value": round(float(df["sales"].sum() / max(df["quantity"].sum(), 1)), 2),
        "monthly_sales": monthly[["month", "sales"]].to_dict("records"),
        "top_products": df.groupby("product", as_index=False)["sales"].sum().sort_values("sales", ascending=False).head(5).to_dict("records"),
        "sales_by_category": df.groupby("category", as_index=False)["sales"].sum().sort_values("sales", ascending=False).to_dict("records"),
        "sales_by_region": df.groupby("region", as_index=False)["sales"].sum().sort_values("sales", ascending=False).to_dict("records"),
        "forecast_accuracy": latest_run.accuracy if latest_run else 0,
        "confidence_score": latest_run.confidence_score if latest_run else 0,
        "forecast": forecast_points(latest_run) if latest_run else [],
        "recent_activity": [{"id": item.id, "action": item.action, "entity_type": item.entity_type, "metadata": json.loads(item.metadata_json), "created_at": item.created_at} for item in activity],
        "filters": {"start_date": start_date, "end_date": end_date, "category": category, "region": region},
    }


def realtime_snapshot(db: Session, dataset_id: int) -> Dict[str, Any]:
    latest_rows = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id).order_by(SalesRecord.date.desc(), SalesRecord.id.desc()).limit(12).all()
    latest_run = db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset_id).order_by(ForecastRun.created_at.desc()).first()
    return {
        "dataset_id": dataset_id,
        "latest_sales": [{
            "date": row.date,
            "product": row.product,
            "category": row.category,
            "region": row.region,
            "quantity": row.quantity,
            "sales": row.sales,
        } for row in latest_rows],
        "rolling_sales": round(sum(row.sales for row in latest_rows), 2),
        "latest_forecast": forecast_points(latest_run) if latest_run else [],
        "refreshed_at": datetime.utcnow(),
    }


def detect_anomalies(db: Session, dataset_id: int) -> List[Dict[str, Any]]:
    rows = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id).order_by(SalesRecord.date).all()
    if not rows:
        return []
    frame = pd.DataFrame([{"date": row.date, "product": row.product, "quantity": row.quantity, "sales": row.sales} for row in rows])
    findings: List[Dict[str, Any]] = []
    for product, product_frame in frame.groupby("product"):
        quantity = product_frame["quantity"].astype(float)
        median = max(float(quantity.median()), 1)
        deviation = (quantity - median).abs()
        threshold = max(float(deviation.median()) * 3, median * 0.35)
        for row in product_frame[deviation > threshold].itertuples(index=False):
            delta = abs(float(row.quantity) - median) / median * 100
            findings.append({
                "product": product,
                "date": row.date,
                "observed_quantity": round(float(row.quantity), 2),
                "expected_quantity": round(median, 2),
                "deviation_percent": round(delta, 2),
                "severity": "high" if delta >= 65 else "medium",
            })
    return sorted(findings, key=lambda item: item["deviation_percent"], reverse=True)[:20]


def seasonal_trends(db: Session, dataset_id: int) -> List[Dict[str, Any]]:
    rows = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id).order_by(SalesRecord.date).all()
    if not rows:
        return []
    frame = pd.DataFrame([{"date": row.date, "quantity": row.quantity, "sales": row.sales} for row in rows])
    frame["date"] = pd.to_datetime(frame["date"])
    frame["month"] = frame["date"].dt.strftime("%b")
    frame["month_number"] = frame["date"].dt.month
    monthly = frame.groupby(["month_number", "month"], as_index=False).agg(quantity=("quantity", "mean"), sales=("sales", "mean")).sort_values("month_number")
    baseline = max(float(monthly["quantity"].mean()), 1)
    monthly["trend_percent"] = ((monthly["quantity"] - baseline) / baseline * 100).round(2)
    monthly["signal"] = monthly["trend_percent"].apply(lambda value: "peak" if value > 12 else "low" if value < -12 else "stable")
    return monthly[["month", "quantity", "sales", "trend_percent", "signal"]].to_dict("records")


def advanced_analytics_payload(db: Session, dataset_id: int) -> Dict[str, Any]:
    records = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id).all()
    latest_run = db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset_id).order_by(ForecastRun.created_at.desc()).first()
    frame = pd.DataFrame([{"product": row.product, "category": row.category, "region": row.region, "quantity": row.quantity, "sales": row.sales} for row in records])
    if frame.empty:
        return {"revenue_prediction": 0, "predicted_units": 0, "inventory_risk": [], "region_forecasts": [], "category_insights": [], "seasonal_trends": [], "anomalies": [], "generated_insights": [], "last_refreshed": datetime.utcnow()}
    product_forecasts: Dict[str, float] = {}
    if latest_run:
        for result in latest_run.results:
            product_forecasts[result.product] = product_forecasts.get(result.product, 0) + result.predicted_demand
    else:
        product_forecasts = frame.groupby("product")["quantity"].sum().to_dict()
    unit_value = float(frame["sales"].sum() / max(frame["quantity"].sum(), 1))
    predicted_units = round(float(sum(product_forecasts.values())), 2)
    revenue_prediction = round(predicted_units * unit_value, 2)
    inventory = []
    for product, demand in product_forecasts.items():
        available = float(frame.loc[frame["product"] == product, "quantity"].tail(3).mean())
        coverage = round(available / max(demand / max(latest_run.periods if latest_run else 1, 1), 1), 2)
        inventory.append({"product": product, "forecast_units": round(demand, 2), "available_baseline": round(available, 2), "coverage_ratio": coverage, "risk": "high" if coverage < 0.8 else "medium" if coverage < 1.15 else "low"})
    region_share = frame.groupby("region", as_index=False)["sales"].sum()
    region_share["share"] = region_share["sales"] / max(float(region_share["sales"].sum()), 1)
    region_forecasts = [{"region": row.region, "predicted_revenue": round(revenue_prediction * row.share, 2), "share_percent": round(row.share * 100, 2)} for row in region_share.itertuples()]
    categories = frame.groupby("category", as_index=False).agg(sales=("sales", "sum"), units=("quantity", "sum")).sort_values("sales", ascending=False)
    category_insights = [{"category": row.category, "sales": round(row.sales, 2), "units": round(row.units, 2), "revenue_share": round(row.sales / max(float(categories["sales"].sum()), 1) * 100, 2)} for row in categories.itertuples()]
    anomalies = detect_anomalies(db, dataset_id)
    seasonal = seasonal_trends(db, dataset_id)
    high_risks = [item["product"] for item in inventory if item["risk"] == "high"]
    strongest_region = region_forecasts[0]["region"] if region_forecasts else "N/A"
    leading_category = category_insights[0]["category"] if category_insights else "N/A"
    insights = [
        f"Projected revenue is ${revenue_prediction:,.2f} based on {predicted_units:,.0f} predicted units.",
        f"{strongest_region} contributes the strongest regional revenue outlook; {leading_category} leads category sales.",
        f"{len(anomalies)} unusual sales movements require review before the next replenishment cycle.",
    ]
    if high_risks:
        insights.append(f"Inventory risk is elevated for {', '.join(high_risks[:3])}; consider replenishment planning.")
    return {
        "revenue_prediction": revenue_prediction,
        "predicted_units": predicted_units,
        "inventory_risk": inventory,
        "region_forecasts": region_forecasts,
        "category_insights": category_insights,
        "seasonal_trends": seasonal,
        "anomalies": anomalies,
        "generated_insights": insights,
        "last_refreshed": datetime.utcnow(),
    }


def automatically_retrain(db: Session, dataset_id: int, user_id: int, periods: int = 6) -> RetrainingJob:
    previous = db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset_id).order_by(ForecastRun.created_at.desc()).first()
    comparison = compare_models(db, dataset_id)
    if not comparison:
        raise HTTPException(status_code=400, detail="Dataset has no training data")
    selected = comparison[0]["model_name"]
    run = train_and_forecast(db, dataset_id, periods, selected)
    job = RetrainingJob(
        dataset_id=dataset_id,
        requested_by=user_id,
        selected_model=selected,
        previous_accuracy=previous.accuracy if previous else 0,
        new_accuracy=run.accuracy,
        status="completed",
    )
    db.add(job)
    db.flush()
    return job


def build_excel_report(db: Session, dataset: Dataset) -> BytesIO:
    output = BytesIO()
    records = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset.id).all()
    latest_run = db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset.id).order_by(ForecastRun.created_at.desc()).first()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        pd.DataFrame([{"date": r.date, "product": r.product, "category": r.category, "region": r.region, "quantity": r.quantity, "sales": r.sales} for r in records]).to_excel(writer, "Historical Sales", index=False)
        pd.DataFrame(forecast_points(latest_run) if latest_run else []).to_excel(writer, "Forecast", index=False)
        pd.DataFrame([{"model": m.model_name, "product": m.product, "rmse": m.rmse, "mae": m.mae, "accuracy": m.accuracy, "confidence": m.confidence_score} for m in latest_run.metrics] if latest_run else []).to_excel(writer, "Model Metrics", index=False)
    output.seek(0)
    return output


def build_pdf_report(db: Session, dataset: Dataset) -> BytesIO:
    output = BytesIO()
    latest_run = db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset.id).order_by(ForecastRun.created_at.desc()).first()
    doc = SimpleDocTemplate(output, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph("Advanced AI Demand Forecasting Report", styles["Title"]), Paragraph("Developed by Yogeshwaran K", styles["Normal"]), Spacer(1, 12)]
    story.append(Paragraph(f"Dataset: {dataset.name}", styles["Normal"]))
    story.append(Paragraph(f"Rows analyzed: {dataset.row_count}", styles["Normal"]))
    if latest_run:
        story.append(Paragraph(f"Model: {latest_run.model_name} | Accuracy: {latest_run.accuracy}% | Confidence: {latest_run.confidence_score}%", styles["Normal"]))
    story.append(Spacer(1, 12))
    rows = [["Date", "Product", "Model", "Demand", "Accuracy"]] + [[str(f.forecast_date), f.product, f.model_name, f"{f.predicted_demand:.2f}", f"{f.accuracy:.1f}%"] for f in (latest_run.results[:24] if latest_run else [])]
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#155E75")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]))
    story.append(table)
    doc.build(story)
    output.seek(0)
    return output


def _records_frame(db: Session, dataset_id: int) -> pd.DataFrame:
    rows = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id).order_by(SalesRecord.date).all()
    return pd.DataFrame([{"date": row.date, "product": row.product, "category": row.category, "region": row.region, "quantity": row.quantity, "sales": row.sales} for row in rows])


def product_recommendations(db: Session, dataset_id: int) -> List[Dict[str, Any]]:
    frame = _records_frame(db, dataset_id)
    if frame.empty:
        return []
    grouped = frame.groupby(["product", "category"], as_index=False).agg(units=("quantity", "sum"), revenue=("sales", "sum"))
    total_revenue = max(float(grouped["revenue"].sum()), 1)
    grouped["score"] = ((grouped["revenue"] / total_revenue) * 65 + (grouped["units"] / max(float(grouped["units"].max()), 1)) * 35).round(2)
    return [{"product": row.product, "category": row.category, "score": row.score, "recommendation": "prioritize replenishment" if row.score >= 70 else "monitor demand"} for row in grouped.sort_values("score", ascending=False).head(10).itertuples()]


def customer_behavior_analysis(db: Session, dataset_id: int) -> List[Dict[str, Any]]:
    frame = _records_frame(db, dataset_id)
    if frame.empty:
        return []
    frame["date"] = pd.to_datetime(frame["date"])
    frame["month"] = frame["date"].dt.strftime("%b %Y")
    rows = frame.groupby(["region", "category"], as_index=False).agg(units=("quantity", "sum"), revenue=("sales", "sum"))
    total = max(float(rows["revenue"].sum()), 1)
    return [{"segment": f"{row.region} / {row.category}", "units": round(row.units, 2), "revenue": round(row.revenue, 2), "share_percent": round(row.revenue / total * 100, 2)} for row in rows.sort_values("revenue", ascending=False).head(12).itertuples()]


def demand_spike_predictions(db: Session, dataset_id: int) -> List[Dict[str, Any]]:
    frame = _records_frame(db, dataset_id)
    if frame.empty:
        return []
    frame["date"] = pd.to_datetime(frame["date"])
    findings = []
    for product, product_frame in frame.groupby("product"):
        monthly = product_frame.set_index("date")["quantity"].resample("MS").sum().reset_index()
        if len(monthly) < 3:
            continue
        recent = float(monthly["quantity"].tail(2).mean())
        baseline = max(float(monthly["quantity"].iloc[:-2].mean()), 1)
        lift = round((recent - baseline) / baseline * 100, 2)
        if lift > 15:
            findings.append({"product": product, "spike_probability": min(99, round(55 + lift / 2, 2)), "trend_lift_percent": lift, "recommended_action": "prepare safety stock"})
    return sorted(findings, key=lambda item: item["spike_probability"], reverse=True)[:10]


def low_stock_predictions(db: Session, dataset_id: int) -> List[Dict[str, Any]]:
    analytics = advanced_analytics_payload(db, dataset_id)
    return [{"product": item["product"], "risk": item["risk"], "coverage_ratio": item["coverage_ratio"], "forecast_units": item["forecast_units"], "suggested_reorder_units": max(0, round(item["forecast_units"] * 0.25 - item["available_baseline"], 2))} for item in analytics["inventory_risk"] if item["risk"] in {"high", "medium"}]


def inventory_optimization_suggestions(db: Session, dataset_id: int) -> List[Dict[str, Any]]:
    risks = low_stock_predictions(db, dataset_id)
    spikes = {item["product"]: item for item in demand_spike_predictions(db, dataset_id)}
    suggestions = []
    for item in risks:
        urgency = "critical" if item["risk"] == "high" or item["product"] in spikes else "planned"
        suggestions.append({"product": item["product"], "urgency": urgency, "suggested_units": item["suggested_reorder_units"], "reason": "low coverage and rising demand" if item["product"] in spikes else "forecast coverage below target"})
    return suggestions


def enterprise_ai_insights(db: Session, dataset_id: int) -> Dict[str, Any]:
    return {
        "recommendations": product_recommendations(db, dataset_id),
        "customer_behavior": customer_behavior_analysis(db, dataset_id),
        "demand_spikes": demand_spike_predictions(db, dataset_id),
        "low_stock_predictions": low_stock_predictions(db, dataset_id),
        "inventory_optimizations": inventory_optimization_suggestions(db, dataset_id),
        "generated_at": datetime.utcnow(),
    }


def forecast_trend_payload(db: Session, dataset_id: int) -> Dict[str, Any]:
    runs = db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset_id).order_by(ForecastRun.created_at.asc()).all()
    accuracy = [{"run_id": run.id, "model_name": run.model_name, "accuracy": run.accuracy, "created_at": run.created_at} for run in runs]
    confidence = [{"run_id": run.id, "model_name": run.model_name, "confidence_score": run.confidence_score, "created_at": run.created_at} for run in runs]
    latest_by_model: Dict[str, ForecastRun] = {}
    for run in runs:
        latest_by_model[run.model_name] = run
    historical = [{"model_name": model, "accuracy": run.accuracy, "confidence_score": run.confidence_score, "predictions": run.total_predictions} for model, run in latest_by_model.items()]
    recommendations = []
    if historical:
        best = sorted(historical, key=lambda item: item["accuracy"], reverse=True)[0]
        recommendations.append(f"{best['model_name']} is currently the strongest model at {best['accuracy']}% accuracy.")
    low_confidence = [item for item in confidence[-5:] if item["confidence_score"] < 70]
    if low_confidence:
        recommendations.append("Recent confidence is below target; retrain with updated sales data before operational use.")
    if not recommendations:
        recommendations.append("Forecast accuracy and confidence are stable across recent runs.")
    return {"accuracy_trends": accuracy, "historical_comparison": historical, "confidence_scores": confidence, "recommendations": recommendations}


def create_default_widgets(db: Session, user_id: int) -> None:
    if db.query(DashboardWidget).filter(DashboardWidget.user_id == user_id).count():
        return
    defaults = [
        ("sales_kpi", "Sales KPI", 1),
        ("forecast_accuracy", "Forecast Accuracy", 2),
        ("inventory_risk", "Inventory Risk", 3),
        ("model_comparison", "Model Comparison", 4),
    ]
    for key, title, position in defaults:
        db.add(DashboardWidget(user_id=user_id, widget_key=key, title=title, position=position))


def evaluate_alert_rules(db: Session, user_id: int, dataset_id: int) -> List[Notification]:
    latest = db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset_id).order_by(ForecastRun.created_at.desc()).first()
    rules = db.query(AlertRule).filter(AlertRule.user_id == user_id, AlertRule.is_active.is_(True)).filter((AlertRule.dataset_id == dataset_id) | (AlertRule.dataset_id.is_(None))).all()
    triggered = []
    for rule in rules:
        value = getattr(latest, rule.metric, None) if latest else None
        if value is None:
            continue
        expr = f"{float(value)} {rule.operator} {float(rule.threshold)}"
        if eval(expr, {"__builtins__": {}}, {}):
            triggered.append(notify(db, user_id, f"Alert: {rule.name}", f"{rule.metric} is {value}, threshold {rule.operator} {rule.threshold}.", "warning"))
    return triggered


def run_due_forecast_schedules(db: Session) -> List[Dict[str, Any]]:
    due = db.query(ForecastSchedule).filter(ForecastSchedule.is_active.is_(True), ForecastSchedule.next_run_at <= datetime.utcnow()).limit(10).all()
    executed = []
    for schedule in due:
        try:
            run = train_and_forecast(db, schedule.dataset_id, schedule.periods, schedule.model_name)
            schedule.last_run_at = datetime.utcnow()
            schedule.next_run_at = schedule.last_run_at + pd.Timedelta(minutes=schedule.interval_minutes).to_pytimedelta()
            notify(db, schedule.created_by, "Scheduled forecast completed", f"{schedule.name} created {run.total_predictions} predictions.", "success")
            log_activity(db, schedule.created_by, "automation.forecast.completed", "dataset", schedule.dataset_id, {"schedule_id": schedule.id, "run_id": run.id})
            if run.accuracy < schedule.alert_threshold:
                notify(db, schedule.created_by, "Forecast accuracy alert", f"{run.model_name} accuracy is {run.accuracy}%, below {schedule.alert_threshold}%.", "warning")
            evaluate_alert_rules(db, schedule.created_by, schedule.dataset_id)
            executed.append({"schedule_id": schedule.id, "status": "completed", "run_id": run.id})
        except Exception as exc:
            notify(db, schedule.created_by, "Scheduled forecast failed", str(exc), "error")
            log_activity(db, schedule.created_by, "automation.forecast.failed", "dataset", schedule.dataset_id, {"schedule_id": schedule.id, "error": str(exc)})
            executed.append({"schedule_id": schedule.id, "status": "failed", "error": str(exc)})
    db.flush()
    return executed

def _json_loads(value: str) -> Dict[str, Any]:
    return json.loads(value or "{}")


def project_access_ids(db: Session, user: User) -> List[int]:
    if user.role in {"admin", "super_admin"}:
        return [row.id for row in db.query(ForecastProject.id).all()]
    owned = [row.id for row in db.query(ForecastProject.id).filter(ForecastProject.owner_id == user.id).all()]
    member = [row.project_id for row in db.query(ProjectMember.project_id).filter(ProjectMember.user_id == user.id).all()]
    return sorted(set(owned + member))


def get_project_or_404(db: Session, project_id: int, user: User) -> ForecastProject:
    project = db.query(ForecastProject).filter(ForecastProject.id == project_id).first()
    if not project or (user.role not in {"admin", "super_admin"} and project.id not in project_access_ids(db, user)):
        raise HTTPException(status_code=404, detail="Forecast project not found")
    return project


def log_project_activity(db: Session, project_id: int, user_id: Optional[int], action: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    db.add(ProjectActivity(project_id=project_id, user_id=user_id, action=action, metadata_json=json.dumps(metadata or {})))


def project_summary_payload(db: Session, project: ForecastProject) -> Dict[str, Any]:
    dataset_ids = [row.dataset_id for row in db.query(ProjectDataset.dataset_id).filter(ProjectDataset.project_id == project.id).all()]
    forecast_count = db.query(ForecastRun).filter(ForecastRun.dataset_id.in_(dataset_ids)).count() if dataset_ids else 0
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "owner_id": project.owner_id,
        "status": project.status,
        "created_at": project.created_at,
        "dataset_count": len(dataset_ids),
        "forecast_count": forecast_count,
    }


def scenario_payload(db: Session, scenario: ForecastScenario) -> Dict[str, Any]:
    results = db.query(ForecastScenarioResult).filter(ForecastScenarioResult.scenario_id == scenario.id).all()
    return {
        "id": scenario.id,
        "project_id": scenario.project_id,
        "dataset_id": scenario.dataset_id,
        "name": scenario.name,
        "sales_growth_percent": scenario.sales_growth_percent,
        "seasonality_percent": scenario.seasonality_percent,
        "demand_factor": scenario.demand_factor,
        "price_change_percent": scenario.price_change_percent,
        "cost_change_percent": scenario.cost_change_percent,
        "status": scenario.status,
        "created_at": scenario.created_at,
        "results": [{"product": row.product, "baseline_demand": row.baseline_demand, "scenario_demand": row.scenario_demand, "revenue_impact": row.revenue_impact, "profit_impact": row.profit_impact} for row in results],
    }


def create_scenario_plan(db: Session, project_id: int, user_id: int, payload: Dict[str, Any]) -> ForecastScenario:
    rows = db.query(SalesRecord).filter(SalesRecord.dataset_id == payload["dataset_id"]).all()
    frame = pd.DataFrame([{"product": row.product, "quantity": row.quantity, "sales": row.sales} for row in rows])
    if frame.empty:
        raise HTTPException(status_code=400, detail="Dataset has no scenario planning data")
    unit_value = float(frame["sales"].sum() / max(frame["quantity"].sum(), 1))
    avg_cost = unit_value * 0.62
    scenario = ForecastScenario(project_id=project_id, created_by=user_id, **payload)
    db.add(scenario)
    db.flush()
    growth = 1 + payload["sales_growth_percent"] / 100
    season = 1 + payload["seasonality_percent"] / 100
    demand_factor = payload["demand_factor"]
    price_factor = 1 + payload["price_change_percent"] / 100
    cost_factor = 1 + payload["cost_change_percent"] / 100
    for row in frame.groupby("product", as_index=False).agg(quantity=("quantity", "sum")).itertuples():
        baseline = float(row.quantity)
        scenario_demand = round(max(0, baseline * growth * season * demand_factor), 2)
        revenue_impact = round((scenario_demand * unit_value * price_factor) - (baseline * unit_value), 2)
        profit_impact = round((scenario_demand * (unit_value * price_factor - avg_cost * cost_factor)) - (baseline * (unit_value - avg_cost)), 2)
        db.add(ForecastScenarioResult(scenario_id=scenario.id, product=row.product, baseline_demand=baseline, scenario_demand=scenario_demand, revenue_impact=revenue_impact, profit_impact=profit_impact))
    log_project_activity(db, project_id, user_id, "scenario.created", {"scenario": scenario.name})
    db.flush()
    return scenario


def scenario_comparison_payload(db: Session, project_id: int) -> Dict[str, Any]:
    scenarios = db.query(ForecastScenario).filter(ForecastScenario.project_id == project_id).order_by(ForecastScenario.created_at.desc()).limit(12).all()
    payloads = [scenario_payload(db, scenario) for scenario in scenarios]
    totals = []
    for item in payloads:
        totals.append({
            "id": item["id"],
            "name": item["name"],
            "demand": round(sum(row["scenario_demand"] for row in item["results"]), 2),
            "revenue_impact": round(sum(row["revenue_impact"] for row in item["results"]), 2),
            "profit_impact": round(sum(row["profit_impact"] for row in item["results"]), 2),
        })
    return {"scenarios": payloads, "totals": totals}


def executive_dashboard_payload(db: Session, user: User, project_id: Optional[int] = None) -> Dict[str, Any]:
    if project_id:
        get_project_or_404(db, project_id, user)
        dataset_ids = [row.dataset_id for row in db.query(ProjectDataset.dataset_id).filter(ProjectDataset.project_id == project_id).all()]
    else:
        query = db.query(Dataset.id)
        if user.role not in {"admin", "super_admin"}:
            query = query.filter(Dataset.owner_id == user.id)
        dataset_ids = [row.id for row in query.all()]
    rows = db.query(SalesRecord).filter(SalesRecord.dataset_id.in_(dataset_ids)).all() if dataset_ids else []
    frame = pd.DataFrame([{"date": row.date, "product": row.product, "category": row.category, "region": row.region, "quantity": row.quantity, "sales": row.sales} for row in rows])
    if frame.empty:
        return {"revenue_forecast": 0, "profit_forecast": 0, "estimated_cost": 0, "growth_impact_percent": 0, "kpis": {}, "cost_analysis": [], "performance": [], "recommendations": ["Upload and assign datasets to unlock executive reporting."]}
    frame["date"] = pd.to_datetime(frame["date"])
    total_sales = float(frame["sales"].sum())
    total_units = float(frame["quantity"].sum())
    unit_value = total_sales / max(total_units, 1)
    revenue_forecast = round(total_sales * 1.12, 2)
    estimated_cost = round(revenue_forecast * 0.62, 2)
    profit_forecast = round(revenue_forecast - estimated_cost, 2)
    monthly = frame.set_index("date")["sales"].resample("MS").sum().reset_index()
    growth = 0
    if len(monthly) >= 2 and monthly["sales"].iloc[-2] > 0:
        growth = round((monthly["sales"].iloc[-1] - monthly["sales"].iloc[-2]) / monthly["sales"].iloc[-2] * 100, 2)
    cost = frame.groupby("category", as_index=False).agg(revenue=("sales", "sum"), units=("quantity", "sum"))
    cost_analysis = [{"category": row.category, "revenue": round(row.revenue, 2), "estimated_cost": round(row.revenue * 0.62, 2), "gross_margin": round(row.revenue * 0.38, 2)} for row in cost.itertuples()]
    performance = frame.groupby("region", as_index=False)["sales"].sum().sort_values("sales", ascending=False).head(8).to_dict("records")
    recommendations = [
        f"Revenue outlook is ${revenue_forecast:,.2f} with estimated gross profit of ${profit_forecast:,.2f}.",
        f"Current growth impact is {growth}% based on the latest monthly sales movement.",
        "Prioritize high-margin categories and review regions with lower contribution before the next forecast cycle.",
    ]
    return {
        "revenue_forecast": revenue_forecast,
        "profit_forecast": profit_forecast,
        "estimated_cost": estimated_cost,
        "growth_impact_percent": growth,
        "kpis": {"datasets": len(dataset_ids), "total_sales": round(total_sales, 2), "total_units": round(total_units, 2), "average_unit_value": round(unit_value, 2)},
        "cost_analysis": cost_analysis,
        "performance": performance,
        "recommendations": recommendations,
    }


def bi_insights_payload(db: Session, dataset_id: int) -> Dict[str, Any]:
    frame = _records_frame(db, dataset_id)
    if frame.empty:
        return {"opportunities": [], "declining_products": [], "high_growth_products": [], "summaries": []}
    frame["date"] = pd.to_datetime(frame["date"])
    opportunities: List[Dict[str, Any]] = []
    declining: List[Dict[str, Any]] = []
    growth_rows: List[Dict[str, Any]] = []
    for product, item in frame.groupby("product"):
        monthly = item.set_index("date")["quantity"].resample("MS").sum().reset_index()
        if len(monthly) < 2:
            continue
        previous = max(float(monthly["quantity"].iloc[-2]), 1)
        latest = float(monthly["quantity"].iloc[-1])
        change = round((latest - previous) / previous * 100, 2)
        row = {"product": product, "latest_units": round(latest, 2), "change_percent": change}
        if change >= 15:
            growth_rows.append(row)
            opportunities.append({**row, "recommendation": "increase availability and campaign allocation"})
        if change <= -15:
            declining.append({**row, "recommendation": "review pricing, placement, or substitution risk"})
    summaries = [
        f"{len(growth_rows)} products show high-growth demand patterns.",
        f"{len(declining)} products are declining and need commercial review.",
        f"{len(opportunities)} demand opportunities are ready for action planning.",
    ]
    return {"opportunities": opportunities[:10], "declining_products": declining[:10], "high_growth_products": growth_rows[:10], "summaries": summaries}


def dataset_comparison_payload(db: Session, dataset_id: int) -> Dict[str, Any]:
    versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version.desc()).all()
    rows = db.query(SalesRecord).filter(SalesRecord.dataset_id == dataset_id).all()
    product_count = len({row.product for row in rows})
    category_count = len({row.category for row in rows})
    region_count = len({row.region for row in rows})
    row_delta = 0
    if len(versions) >= 2:
        row_delta = versions[0].row_count - versions[1].row_count
    return {"dataset_id": dataset_id, "versions": versions, "row_delta": row_delta, "product_count": product_count, "category_count": category_count, "region_count": region_count}


def accuracy_center_payload(db: Session, dataset_id: int) -> Dict[str, Any]:
    runs = db.query(ForecastRun).filter(ForecastRun.dataset_id == dataset_id).order_by(ForecastRun.created_at.asc()).all()
    performance = compare_models(db, dataset_id)
    trends = [{"run_id": run.id, "model_name": run.model_name, "accuracy": run.accuracy, "confidence_score": run.confidence_score, "created_at": run.created_at} for run in runs]
    historical = [{"run_id": run.id, "rmse": run.rmse, "mae": run.mae, "accuracy": run.accuracy, "total_predictions": run.total_predictions} for run in runs[-20:]]
    improvement = 0
    if len(runs) >= 2:
        improvement = round(runs[-1].accuracy - runs[0].accuracy, 2)
    report = [
        f"{len(runs)} forecast runs are available for evaluation.",
        f"Model accuracy improved by {improvement}% from first to latest run.",
        "Use the strongest model for executive reports and retrain when confidence falls below target.",
    ]
    return {"model_performance": performance, "accuracy_trends": trends, "historical_performance": historical, "improvement_summary": {"run_count": len(runs), "accuracy_delta": improvement}, "evaluation_report": report}
