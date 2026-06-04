import React, { useEffect, useState } from "react";
import { CalendarClock, Play, RefreshCw } from "lucide-react";
import api from "../api/client";
import DatasetPicker from "../components/DatasetPicker";
import DataTable from "../components/DataTable";

export default function AutomationPage({ datasets, selectedDatasetId, setSelectedDatasetId, refresh }) {
  const [schedules, setSchedules] = useState([]);
  const [form, setForm] = useState({ name: "Daily ensemble forecast", model_name: "ensemble", periods: 6, interval_minutes: 1440, alert_threshold: 70 });
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const { data } = await api.get("/automation/schedules");
    setSchedules(data);
  };
  useEffect(() => { load(); }, []);

  const create = async (event) => {
    event.preventDefault();
    if (!selectedDatasetId) return;
    setBusy(true);
    try {
      await api.post("/automation/schedules", { ...form, dataset_id: Number(selectedDatasetId), periods: Number(form.periods), interval_minutes: Number(form.interval_minutes), alert_threshold: Number(form.alert_threshold), is_active: true });
      await load();
      await refresh?.();
    } finally {
      setBusy(false);
    }
  };

  const runDue = async () => {
    setBusy(true);
    try {
      await api.post("/automation/run-due");
      await load();
      await refresh?.();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="page-eyebrow">Smart automation</p><h2 className="page-title">Recurring forecast operations</h2></div>
        <DatasetPicker datasets={datasets} selectedDatasetId={selectedDatasetId} setSelectedDatasetId={setSelectedDatasetId} />
      </div>
      <form onSubmit={create} className="panel grid gap-3 lg:grid-cols-[1.2fr_0.9fr_0.7fr_0.8fr_0.7fr_auto]">
        <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Schedule name" />
        <select className="input" value={form.model_name} onChange={(e) => setForm({ ...form, model_name: e.target.value })}><option value="ensemble">Ensemble</option><option value="random_forest">Random Forest</option><option value="xgboost">XGBoost</option><option value="prophet">Prophet</option><option value="linear_regression">Linear Regression</option></select>
        <input className="input" type="number" min="1" max="36" value={form.periods} onChange={(e) => setForm({ ...form, periods: e.target.value })} />
        <input className="input" type="number" min="15" value={form.interval_minutes} onChange={(e) => setForm({ ...form, interval_minutes: e.target.value })} />
        <input className="input" type="number" min="0" max="100" value={form.alert_threshold} onChange={(e) => setForm({ ...form, alert_threshold: e.target.value })} />
        <button className="secondary-button h-12" disabled={busy || !selectedDatasetId}><CalendarClock size={17}/> Save</button>
      </form>
      <section className="panel">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h3 className="text-lg font-black">Automation queue</h3><button onClick={runDue} disabled={busy} className="secondary-button inline-flex items-center gap-2"><Play size={16}/>Run due now</button></div>
        <DataTable columns={[
          { key: "name", label: "Schedule" },
          { key: "model_name", label: "Model" },
          { key: "interval_minutes", label: "Interval" },
          { key: "next_run_at", label: "Next run", render: (row) => new Date(row.next_run_at).toLocaleString() },
          { key: "is_active", label: "Status", render: (row) => row.is_active ? "Active" : "Paused" }
        ]} rows={schedules} />
      </section>
    </div>
  );
}


