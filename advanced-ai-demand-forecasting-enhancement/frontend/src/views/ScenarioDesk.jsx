import React, { useEffect, useState } from "react";
import { PlayCircle } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import gateway from "../services/gateway";
import WorkbookSelect from "../widgets/WorkbookSelect";

export default function ScenarioDesk({ workbooks, activeWorkbook, setActiveWorkbook, refresh }) {
  const [algorithms, setAlgorithms] = useState([]);
  const [algorithm, setAlgorithm] = useState("linear");
  const [horizon, setHorizon] = useState(6);
  const [projection, setProjection] = useState([]);
  const [comparison, setComparison] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    gateway.get("/planning/algorithms").then(({ data }) => setAlgorithms(data.records || []));
  }, []);

  const run = async () => {
    if (!activeWorkbook) return;
    setBusy(true);
    try {
      const { data } = await gateway.post(`/planning/${activeWorkbook}/scenario`, { algorithm, horizon: Number(horizon) });
      setProjection(data.projections);
      await refresh?.();
    } finally {
      setBusy(false);
    }
  };

  const compare = async () => {
    if (!activeWorkbook) return;
    const { data } = await gateway.get(`/planning/${activeWorkbook}/compare`);
    setComparison(data);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="section-label">Scenario lab</p><h2 className="section-title">Forecast planning scenarios</h2></div>
        <WorkbookSelect workbooks={workbooks} value={activeWorkbook} onChange={setActiveWorkbook} />
      </div>
      <section className="surface grid gap-4 md:grid-cols-[1fr_1fr_auto_auto]">
        <select className="field" value={algorithm} onChange={(event) => setAlgorithm(event.target.value)}>{algorithms.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
        <input className="field" type="number" min="1" max="24" value={horizon} onChange={(event) => setHorizon(event.target.value)} />
        <button className="primary-action" onClick={run} disabled={busy}><PlayCircle size={18}/>{busy ? "Running" : "Run Scenario"}</button>
        <button className="secondary-action" onClick={compare}>Compare</button>
      </section>
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="surface"><h3 className="mb-4 text-lg font-black">Projection curve</h3>{projection.length ? <ResponsiveContainer width="100%" height={320}><LineChart data={projection}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="target_date"/><YAxis/><Tooltip/><Line dataKey="expected_units" stroke="#15803d" strokeWidth={3}/><Line dataKey="high_estimate" stroke="#84cc16" strokeDasharray="4 4"/><Line dataKey="low_estimate" stroke="#22c55e" strokeDasharray="4 4"/></LineChart></ResponsiveContainer> : <p className="soft-empty">Run a scenario to view projections.</p>}</section>
        <section className="surface"><h3 className="mb-4 text-lg font-black">Algorithm comparison</h3>{comparison.length ? <ResponsiveContainer width="100%" height={320}><BarChart data={comparison}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="algorithm"/><YAxis/><Tooltip/><Bar dataKey="quality_score" fill="#15803d" radius={[10,10,0,0]}/><Bar dataKey="confidence" fill="#86efac" radius={[10,10,0,0]}/></BarChart></ResponsiveContainer> : <p className="soft-empty">Compare algorithms after importing data.</p>}</section>
      </div>
    </div>
  );
}
