# Advanced AI Demand Forecasting Enhancement

Developed for Priya

A full-stack green and white corporate demand intelligence platform with FastAPI, React, JWT authentication, forecasting engines, analytics, reports, notifications, and admin controls.

## Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn server.app:app --reload --host 127.0.0.1 --port 8100
```

API docs:

```text
http://127.0.0.1:8100/docs
```

## Frontend

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5274 --strictPort
```

App:

```text
http://127.0.0.1:5274
```

Register the first user to become admin.
