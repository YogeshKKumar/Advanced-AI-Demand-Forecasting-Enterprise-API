import React, { useEffect, useState } from "react";
import { GitBranch, ShieldCheck, TimerReset } from "lucide-react";
import api from "../api/client";
import MetricCard from "../components/MetricCard";

export default function GovernanceCenterPage() {
  const [organizations, setOrganizations] = useState([]);
  const [orgId, setOrgId] = useState("");
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/organizations").then(({ data }) => { setOrganizations(data); if (data[0]) setOrgId(String(data[0].id)); }); }, []);
  useEffect(() => { if (orgId) api.get(`/governance/${orgId}`).then(({ data }) => setData(data)); }, [orgId]);
  return (
    <div className="space-y-6">
      <select className="input max-w-xs" value={orgId} onChange={(e) => setOrgId(e.target.value)}>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="Lifecycle Stages" value={Object.keys(data?.lifecycle_counts || {}).length} icon={GitBranch} tone="ocean" />
        <MetricCard title="Approval States" value={Object.keys(data?.approval_counts || {}).length} icon={ShieldCheck} tone="mint" />
        <MetricCard title="Version Events" value={(data?.version_history || []).length} icon={TimerReset} tone="amber" />
      </div>
      <section className="grid gap-4 lg:grid-cols-[1fr_0.8fr]">
        <div className="panel"><h2 className="section-title mb-4">Governance Timeline</h2>{(data?.recent_events || []).map((item) => <div key={item.id} className="mb-3 rounded-lg border p-3"><p className="font-bold">{item.event_type}</p><p className="text-sm text-slate-500">Stage {item.lifecycle_stage} | Version {item.version}</p></div>)}{!data?.recent_events?.length && <p className="empty-state">No governance events recorded yet.</p>}</div>
        <div className="panel"><h2 className="section-title mb-4">Governance Recommendations</h2>{(data?.recommendations || []).map((item) => <p key={item} className="mb-3 rounded-lg bg-slate-50 p-3 text-sm dark:bg-white/5">{item}</p>)}</div>
      </section>
    </div>
  );
}
