from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="analyst", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    datasets: Mapped[List["Dataset"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        Index("ix_datasets_owner_status_created", "owner_id", "status", "created_at"),
        Index("ix_datasets_name_created", "name", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="ready", index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    owner: Mapped[User] = relationship(back_populates="datasets")
    records: Mapped[List["SalesRecord"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")
    forecast_runs: Mapped[List["ForecastRun"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class SalesRecord(Base):
    __tablename__ = "sales_records"
    __table_args__ = (
        UniqueConstraint("dataset_id", "date", "product", "region", name="uq_dataset_date_product_region"),
        Index("ix_sales_dataset_date_product", "dataset_id", "date", "product"),
        Index("ix_sales_filters", "dataset_id", "category", "region"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    date = mapped_column(Date, index=True)
    product: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(120), default="General", index=True)
    region: Mapped[str] = mapped_column(String(120), default="All Regions", index=True)
    quantity: Mapped[float] = mapped_column(Float)
    sales: Mapped[float] = mapped_column(Float)

    dataset: Mapped[Dataset] = relationship(back_populates="records")


class ForecastRun(Base):
    __tablename__ = "forecast_runs"
    __table_args__ = (Index("ix_forecast_runs_dataset_created", "dataset_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    model_name: Mapped[str] = mapped_column(String(80), index=True)
    periods: Mapped[int] = mapped_column(Integer, default=6)
    status: Mapped[str] = mapped_column(String(40), default="completed", index=True)
    rmse: Mapped[float] = mapped_column(Float, default=0)
    mae: Mapped[float] = mapped_column(Float, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0)
    total_predictions: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    dataset: Mapped[Dataset] = relationship(back_populates="forecast_runs")
    results: Mapped[List["ForecastResult"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    metrics: Mapped[List["ModelMetric"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class ForecastResult(Base):
    __tablename__ = "forecast_results"
    __table_args__ = (Index("ix_forecast_results_run_product_date", "run_id", "product", "forecast_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("forecast_runs.id"), index=True)
    product: Mapped[str] = mapped_column(String(255), index=True)
    model_name: Mapped[str] = mapped_column(String(80), index=True)
    forecast_date = mapped_column(Date, index=True)
    predicted_demand: Mapped[float] = mapped_column(Float)
    lower_bound: Mapped[float] = mapped_column(Float, default=0)
    upper_bound: Mapped[float] = mapped_column(Float, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[ForecastRun] = relationship(back_populates="results")


class ModelMetric(Base):
    __tablename__ = "model_metrics"
    __table_args__ = (Index("ix_model_metrics_run_model", "run_id", "model_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("forecast_runs.id"), index=True)
    model_name: Mapped[str] = mapped_column(String(80), index=True)
    product: Mapped[str] = mapped_column(String(255), index=True)
    rmse: Mapped[float] = mapped_column(Float, default=0)
    mae: Mapped[float] = mapped_column(Float, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[ForecastRun] = relationship(back_populates="metrics")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(40), default="info")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="notifications")


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (Index("ix_activity_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), default="system")
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ApiMetric(Base):
    __tablename__ = "api_metrics"
    __table_args__ = (
        Index("ix_api_metrics_endpoint_created", "endpoint", "created_at"),
        Index("ix_api_metrics_status_created", "status_code", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(255), index=True)
    method: Mapped[str] = mapped_column(String(12))
    status_code: Mapped[int] = mapped_column(Integer, index=True)
    duration_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"
    __table_args__ = (Index("ix_anomalies_dataset_date", "dataset_id", "detected_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    product: Mapped[str] = mapped_column(String(255), index=True)
    observed_date = mapped_column(Date, index=True)
    observed_quantity: Mapped[float] = mapped_column(Float)
    expected_quantity: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(40), index=True)
    deviation_percent: Mapped[float] = mapped_column(Float)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class RetrainingJob(Base):
    __tablename__ = "retraining_jobs"
    __table_args__ = (Index("ix_retraining_dataset_created", "dataset_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    selected_model: Mapped[str] = mapped_column(String(80))
    previous_accuracy: Mapped[float] = mapped_column(Float, default=0)
    new_accuracy: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(40), default="completed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
