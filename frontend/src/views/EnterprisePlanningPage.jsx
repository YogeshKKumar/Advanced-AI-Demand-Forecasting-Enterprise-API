import React, { useEffect, useState } from "react";
import { BarChart3, Target, TrendingUp } from "lucide-react";
import api from "../api/client";
import MetricCard from "../components/MetricCard";

export default function EnterprisePlanningPage() {
  const [organizations, setOrganizations] = useState([]);
  const [orgId, setOrgId] = useState("");
  const [horizon, setHorizon] = useState("annual");
  const [planning, setPlanning] = useState(null);

  useEffect(() => { api.get("/organizations").then(({ data }) => { setOrganizations(data); if (data[0]) setOrgId(String(data[0].id)); }); }, []);
  useEffect(() => { if (orgId) api.get(`/planning/${orgId}?horizon=${horizon}`).then(({ data }) => setPlanning(data)); }, [orgId, horizon]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-3">
        <select className="input max-w-xs" value={orgId} onChange={(e) => setOrgId(e.target.value)}>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <select className="input max-w-xs" value={horizon} onChange={(e) => setHorizon(e.target.value)}><option value="annual">Annual Planning</option><option value="quarterly">Quarterly Planning</option></select>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="Forecast Revenue" value={`$${Number(planning?.forecast_totals?.revenue || 0).toLocaleString()}`} icon={TrendingUp} tone="ocean" />
        <MetricCard title="Forecast Demand" value={Number(planning?.forecast_totals?.demand || 0).toLocaleString()} icon={BarChart3} tone="mint" />
        <MetricCard title="Forecast Margin" value={`$${Number(planning?.forecast_totals?.margin || 0).toLocaleString()}`} icon={Target} tone="amber" />
      </div>
      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel"><h2 className="section-title mb-4">Target Attainment</h2>{(planning?.target_attainment || []).map((item) => <div key={item.target_id} className="mb-3 rounded-lg border p-3"><p className="font-bold">{item.name}</p><p className="text-sm text-slate-500">Revenue {item.revenue_attainment}% | Demand {item.demand_attainment}% | Margin {item.margin_attainment}%</p></div>)}{!planning?.target_attainment?.length && <p className="empty-state">Create planning targets from Swagger or admin workflow to populate attainment.</p>}</div>
        <div className="panel"><h2 className="section-title mb-4">Planning Recommendations</h2><div className="space-y-3">{(planning?.recommendations || []).map((item) => <p key={item} className="rounded-lg bg-slate-50 p-3 text-sm dark:bg-white/5">{item}</p>)}</div></div>
      </section>
    </div>
  );
}
