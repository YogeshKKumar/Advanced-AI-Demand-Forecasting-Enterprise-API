# Advanced AI Demand Forecasting Enterprise Platform

Developed by Yogeshwaran K

Enterprise full-stack AI demand forecasting platform built with FastAPI and React. Phase 4 adds real-time sales monitoring, automatic ensemble forecast refresh, model retraining, anomaly and seasonal intelligence, AI-generated insights, inventory risk analytics, global search, three-level permissions, cached dashboards, and API performance monitoring.

## Roles

- `super_admin`: user and system administration plus all operational features.
- `analyst`: upload data, create forecasts, run retraining, and export reports.
- `viewer`: dashboard, analytics, reports, and read-only monitoring of authorized datasets.

The first account registered is assigned `super_admin`.

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

## Demo Credentials

Register the first account to automatically become an admin.
