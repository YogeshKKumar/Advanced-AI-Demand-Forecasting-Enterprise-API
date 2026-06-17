import React, { useEffect, useState } from "react";
import { Gauge, ShieldAlert, Target } from "lucide-react";
import api from "../api/client";
import MetricCard from "../components/MetricCard";

export default function QualityKpiPage({ datasets, selectedDatasetId }) {
  const [organizations, setOrganizations] = useState([]);
  const [orgId, setOrgId] = useState("");
  const [kpi, setKpi] = useState(null);
  const [quality, setQuality] = useState([]);
  useEffect(() => { api.get("/organizations").then(({ data }) => { setOrganizations(data); if (data[0]) setOrgId(String(data[0].id)); }); }, []);
  useEffect(() => { if (orgId) api.get(`/kpis/${orgId}`).then(({ data }) => setKpi(data)); }, [orgId]);
  useEffect(() => { if (selectedDatasetId) api.get(`/data-quality/${selectedDatasetId}/history`).then(({ data }) => setQuality(data)); }, [selectedDatasetId]);
  const runQuality = async () => {
    if (!selectedDatasetId) return;
    await api.post(`/data-quality/${selectedDatasetId}${orgId ? `?organization_id=${orgId}` : ""}`);
    const { data } = await api.get(`/data-quality/${selectedDatasetId}/history`);
    setQuality(data);
  };
  const latest = quality[0];
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-3">
        <select className="input max-w-xs" value={orgId} onChange={(e) => setOrgId(e.target.value)}>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <button className="secondary-button" onClick={runQuality}>Generate Quality Report</button>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="Quality Score" value={latest?.score ?? 0} icon={Gauge} tone="mint" />
        <MetricCard title="Active KPIs" value={kpi?.items?.length || 0} icon={Target} tone="ocean" />
        <MetricCard title="KPI Alerts" value={kpi?.alerts?.length || 0} icon={ShieldAlert} tone="rose" />
      </div>
      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel"><h2 className="section-title mb-4">Custom KPI Performance</h2>{(kpi?.items || []).map((item) => <div key={item.id} className="mb-3 rounded-lg border p-3"><p className="font-bold">{item.name}</p><p className="text-sm text-slate-500">{item.current_value} / {item.target_value} {item.unit} | {item.status}</p></div>)}{!kpi?.items?.length && <p className="empty-state">No custom KPIs created yet.</p>}</div>
        <div className="panel"><h2 className="section-title mb-4">Data Quality History</h2>{quality.map((item) => <div key={item.id} className="mb-3 rounded-lg border p-3"><p className="font-bold">Score {item.score}</p><p className="text-sm text-slate-500">Completeness {item.completeness}% | Consistency {item.consistency}% | Duplicates {item.duplicate_count}</p></div>)}{!quality.length && <p className="empty-state">No quality reports generated for selected dataset.</p>}</div>
      </section>
    </div>
  );
}
