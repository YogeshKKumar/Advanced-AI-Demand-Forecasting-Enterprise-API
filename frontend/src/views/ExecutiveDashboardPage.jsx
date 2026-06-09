import React, { useEffect, useState } from "react";
import { BarChart3, DollarSign, FileDown, TrendingUp, WalletCards } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../api/client";
import MetricCard from "../components/MetricCard";

export default function ExecutiveDashboardPage() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [data, setData] = useState(null);

  useEffect(() => { api.get("/projects").then(({ data }) => { setProjects(data); if (data[0]) setProjectId(String(data[0].id)); }); }, []);
  useEffect(() => {
    const suffix = projectId ? `?project_id=${projectId}` : "";
    api.get(`/bi/executive-dashboard${suffix}`).then(({ data }) => setData(data));
  }, [projectId]);

  const downloadSummary = async () => {
    if (!projectId) return;
    const { data } = await api.get(`/reports/executive/${projectId}`);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "executive-summary.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="page-eyebrow">Business intelligence</p><h2 className="page-title">Executive dashboard</h2></div><div className="flex gap-2"><select className="input" value={projectId} onChange={(e) => setProjectId(e.target.value)}>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select><button className="icon-button" onClick={downloadSummary} title="Download summary"><FileDown size={18}/></button></div></div>
      {!data ? <p className="empty">Loading executive intelligence.</p> : <>
        <div className="grid gap-4 md:grid-cols-4">
          <MetricCard icon={DollarSign} label="Revenue Forecast" value={`$${Number(data.revenue_forecast).toLocaleString()}`} trend="Forward revenue" tone="mint"/>
          <MetricCard icon={WalletCards} label="Profit Forecast" value={`$${Number(data.profit_forecast).toLocaleString()}`} trend="Projected gross profit"/>
          <MetricCard icon={BarChart3} label="Estimated Cost" value={`$${Number(data.estimated_cost).toLocaleString()}`} trend="Cost model"/>
          <MetricCard icon={TrendingUp} label="Growth Impact" value={`${data.growth_impact_percent}%`} trend="Monthly movement" tone="amber"/>
        </div>
        <div className="grid gap-5 xl:grid-cols-2">
          <section className="panel"><h3 className="mb-4 text-lg font-black">Cost analysis</h3><ResponsiveContainer width="100%" height={300}><BarChart data={data.cost_analysis}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="category"/><YAxis/><Tooltip/><Bar dataKey="revenue" fill="#155e75"/><Bar dataKey="gross_margin" fill="#14b8a6"/></BarChart></ResponsiveContainer></section>
          <section className="panel"><h3 className="mb-4 text-lg font-black">Business recommendations</h3><div className="space-y-3">{data.recommendations.map((item) => <p className="insight-row" key={item}>{item}</p>)}</div></section>
        </div>
      </>}
    </div>
  );
}
