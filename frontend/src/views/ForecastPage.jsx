import React, { useEffect, useState } from "react";
import { BrainCircuit, GitCompareArrows, Play, RefreshCw, ShieldAlert } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../api/client";
import DatasetPicker from "../components/DatasetPicker";

export default function ForecastPage({ datasets, selectedDatasetId, setSelectedDatasetId, refresh }) {
  const [models, setModels] = useState([]);
  const [model, setModel] = useState("linear_regression");
  const [periods, setPeriods] = useState(6);
  const [forecast, setForecast] = useState([]);
  const [comparison, setComparison] = useState([]);
  const [history, setHistory] = useState([]);
  const [retraining, setRetraining] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [seasonality, setSeasonality] = useState([]);
  const [historyFilter, setHistoryFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [forecastInsights, setForecastInsights] = useState(null);

  const load = async () => {
    const modelRes = await api.get("/forecast/models");
    setModels(modelRes.data.items || []);
    if (selectedDatasetId) {
      const [compareRes, historyRes, anomalyRes, seasonRes, insightRes] = await Promise.all([
        api.get(`/forecast/${selectedDatasetId}/compare`),
        api.get(`/forecast/${selectedDatasetId}/history`),
        api.get(`/optimization/${selectedDatasetId}/anomalies`),
        api.get(`/optimization/${selectedDatasetId}/seasonality`),
        api.get(`/forecast/${selectedDatasetId}/insights`)
      ]);
      setComparison(compareRes.data);
      setHistory(historyRes.data);
      setAnomalies(anomalyRes.data.items || []);
      setSeasonality(seasonRes.data.items || []);
      setForecastInsights(insightRes.data);
    }
  };

  const retrain = async () => {
    if (!selectedDatasetId) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/optimization/${selectedDatasetId}/retrain?periods=${periods}`);
      setRetraining(data);
      await refresh?.();
      await load();
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { load(); }, [selectedDatasetId]);

  const runForecast = async () => {
    if (!selectedDatasetId) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/forecast/${selectedDatasetId}`, { model_name: model, periods: Number(periods) });
      setForecast(data.items);
      await refresh?.();
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="page-eyebrow">AI forecasting</p><h2 className="page-title">Model lab and comparison</h2></div>
        <DatasetPicker datasets={datasets} selectedDatasetId={selectedDatasetId} setSelectedDatasetId={setSelectedDatasetId} />
      </div>
      <div className="panel grid gap-4 md:grid-cols-[1fr_1fr_0.6fr_auto_auto]">
        <select className="input" value={model} onChange={(event) => setModel(event.target.value)}>{models.map((item) => <option key={item.name} value={item.name}>{item.label}</option>)}</select>
        <input className="input" type="range" min="1" max="36" value={periods} onChange={(event) => setPeriods(event.target.value)} />
        <div className="rounded-lg bg-slate-100 px-4 py-3 text-center font-black dark:bg-white/10">{periods} months</div>
        <button onClick={runForecast} disabled={!selectedDatasetId || busy} className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-ocean px-6 font-black text-white transition hover:-translate-y-0.5 disabled:opacity-50"><Play size={18}/>{busy ? "Training..." : "Run"}</button>
        <button onClick={retrain} disabled={!selectedDatasetId || busy} className="secondary-button inline-flex h-12 items-center gap-2"><RefreshCw size={17}/>Auto Retrain</button>
      </div>
      {retraining && <div className="panel flex flex-wrap items-center gap-3 text-sm"><BrainCircuit size={20} className="text-mint"/><b>Optimization complete:</b><span>{retraining.selected_model}</span><span className="text-slate-500">Accuracy {retraining.previous_accuracy}% to {retraining.new_accuracy}%</span></div>}
      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="panel"><h3 className="mb-4 flex items-center gap-2 text-lg font-black"><BrainCircuit size={20}/> Forecast visualization</h3>{forecast.length === 0 ? <p className="empty">Run a forecast to view predictions.</p> : <ResponsiveContainer width="100%" height={340}><LineChart data={forecast}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis/><Tooltip/><Line dataKey="predicted_demand" stroke="#155e75" strokeWidth={3}/><Line dataKey="upper_bound" stroke="#f59e0b" strokeDasharray="5 5"/><Line dataKey="lower_bound" stroke="#8b5cf6" strokeDasharray="5 5"/></LineChart></ResponsiveContainer>}</section>
        <section className="panel"><h3 className="mb-4 flex items-center gap-2 text-lg font-black"><GitCompareArrows size={20}/> Model comparison</h3>{comparison.length === 0 ? <p className="empty">Upload data to compare models.</p> : <ResponsiveContainer width="100%" height={340}><BarChart data={comparison}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="model_name"/><YAxis/><Tooltip/><Bar dataKey="average_accuracy" fill="#14b8a6" radius={[8,8,0,0]}/><Bar dataKey="confidence_score" fill="#155e75" radius={[8,8,0,0]}/></BarChart></ResponsiveContainer>}</section>
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="panel"><h3 className="mb-4 flex items-center gap-2 text-lg font-black"><ShieldAlert size={20}/> Anomaly Watch</h3>{anomalies.length === 0 ? <p className="empty">No unusual patterns detected.</p> : <div className="space-y-2">{anomalies.slice(0, 5).map((item) => <div className="risk-row" key={`${item.product}-${item.date}`}><span className={`risk-pill risk-${item.severity}`}>{item.severity}</span><b>{item.product}</b><span className="ml-auto text-sm">{item.deviation_percent}% deviation</span></div>)}</div>}</section>
        <section className="panel"><h3 className="mb-4 text-lg font-black">Seasonal Signals</h3>{seasonality.length === 0 ? <p className="empty">No seasonal trends yet.</p> : <ResponsiveContainer width="100%" height={220}><BarChart data={seasonality}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="month"/><YAxis/><Tooltip/><Bar dataKey="trend_percent" fill="#f59e0b" radius={[7,7,0,0]}/></BarChart></ResponsiveContainer>}</section>
      </div>
            {forecastInsights && <section className="panel"><h3 className="mb-4 text-lg font-black">Accuracy and confidence recommendations</h3><div className="grid gap-3 md:grid-cols-3">{forecastInsights.recommendations.map((item) => <p className="insight-row" key={item}>{item}</p>)}</div></section>}
      <section className="panel">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h3 className="text-lg font-black">Forecast history</h3><input className="input h-10" placeholder="Filter model history" value={historyFilter} onChange={(event) => setHistoryFilter(event.target.value)} /></div>
        <div className="overflow-auto">
          <table className="data-table"><thead><tr><th>Run</th><th>Model</th><th>Accuracy</th><th>RMSE</th><th>MAE</th><th>Confidence</th><th>Created</th></tr></thead><tbody>{history.filter((run) => run.model_name.toLowerCase().includes(historyFilter.toLowerCase())).map((run) => <tr key={run.id}><td>#{run.id}</td><td>{run.model_name}</td><td>{run.accuracy}%</td><td>{run.rmse}</td><td>{run.mae}</td><td>{run.confidence_score}%</td><td>{new Date(run.created_at).toLocaleString()}</td></tr>)}</tbody></table>
        </div>
      </section>
    </div>
  );
}



