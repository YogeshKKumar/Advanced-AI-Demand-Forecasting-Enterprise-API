import React, { useEffect, useState } from "react";
import { GitCompareArrows, Save } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../api/client";
import DatasetPicker from "../components/DatasetPicker";
import DataTable from "../components/DataTable";

export default function ScenarioPlannerPage({ datasets, selectedDatasetId, setSelectedDatasetId }) {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [comparison, setComparison] = useState({ scenarios: [], totals: [] });
  const [form, setForm] = useState({ name: "Growth scenario", sales_growth_percent: 12, seasonality_percent: 5, demand_factor: 1.05, price_change_percent: 3, cost_change_percent: 2 });

  const loadProjects = async () => {
    const { data } = await api.get("/projects");
    setProjects(data);
    if (!projectId && data[0]) setProjectId(String(data[0].id));
  };
  const loadComparison = async () => {
    if (!projectId) return;
    const { data } = await api.get(`/projects/${projectId}/scenarios/compare`);
    setComparison(data);
  };
  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { loadComparison(); }, [projectId]);

  const save = async (event) => {
    event.preventDefault();
    if (!projectId || !selectedDatasetId) return;
    await api.post(`/projects/${projectId}/scenarios`, { ...form, dataset_id: Number(selectedDatasetId), sales_growth_percent: Number(form.sales_growth_percent), seasonality_percent: Number(form.seasonality_percent), demand_factor: Number(form.demand_factor), price_change_percent: Number(form.price_change_percent), cost_change_percent: Number(form.cost_change_percent) });
    await loadComparison();
  };

  return (
    <div className="space-y-6">
      <div><p className="page-eyebrow">Advanced scenario planning</p><h2 className="page-title">What-if analysis</h2></div>
      <form onSubmit={save} className="panel grid gap-3 lg:grid-cols-4">
        <select className="input" value={projectId} onChange={(e) => setProjectId(e.target.value)}>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select>
        <DatasetPicker datasets={datasets} selectedDatasetId={selectedDatasetId} setSelectedDatasetId={setSelectedDatasetId}/>
        <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}/>
        <button className="secondary-button h-12 inline-flex items-center gap-2"><Save size={16}/>Save scenario</button>
        {["sales_growth_percent", "seasonality_percent", "demand_factor", "price_change_percent", "cost_change_percent"].map((key) => <label className="decision-card" key={key}><span className="text-xs font-black uppercase text-slate-400">{key.replaceAll("_", " ")}</span><input className="input mt-2 w-full" type="number" step="0.05" value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })}/></label>)}
      </form>
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="panel"><h3 className="mb-4 flex items-center gap-2 text-lg font-black"><GitCompareArrows size={19}/>Scenario comparison</h3><ResponsiveContainer width="100%" height={300}><BarChart data={comparison.totals}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="name"/><YAxis/><Tooltip/><Bar dataKey="revenue_impact" fill="#155e75"/><Bar dataKey="profit_impact" fill="#14b8a6"/></BarChart></ResponsiveContainer></section>
        <section className="panel"><h3 className="mb-4 text-lg font-black">Saved scenarios</h3><DataTable columns={[{ key: "name", label: "Scenario" }, { key: "demand", label: "Demand" }, { key: "revenue_impact", label: "Revenue impact" }, { key: "profit_impact", label: "Profit impact" }]} rows={comparison.totals}/></section>
      </div>
    </div>
  );
}
