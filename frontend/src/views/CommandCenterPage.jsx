import React, { useEffect, useState } from "react";
import { Activity, AlertTriangle, BadgeDollarSign, LineChart } from "lucide-react";
import api from "../api/client";
import MetricCard from "../components/MetricCard";

export default function CommandCenterPage() {
  const [organizations, setOrganizations] = useState([]);
  const [orgId, setOrgId] = useState("");
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/organizations").then(({ data }) => { setOrganizations(data); if (data[0]) setOrgId(String(data[0].id)); }); }, []);
  useEffect(() => { if (orgId) api.get(`/command-center/${orgId}`).then(({ data }) => setData(data)); }, [orgId]);
  return (
    <div className="space-y-6">
      <select className="input max-w-xs" value={orgId} onChange={(e) => setOrgId(e.target.value)}>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard title="Revenue" value={`$${Number(data?.metrics?.revenue || 0).toLocaleString()}`} icon={BadgeDollarSign} tone="ocean" />
        <MetricCard title="Demand" value={Number(data?.metrics?.demand || 0).toLocaleString()} icon={Activity} tone="mint" />
        <MetricCard title="Accuracy" value={`${data?.metrics?.latest_accuracy || 0}%`} icon={LineChart} tone="amber" />
        <MetricCard title="Alerts" value={data?.executive_alerts?.length || 0} icon={AlertTriangle} tone="rose" />
      </div>
      <section className="grid gap-4 lg:grid-cols-3">
        <div className="panel lg:col-span-2"><h2 className="section-title mb-4">Business Performance Summary</h2>{(data?.business_summary || []).map((item) => <div key={item.region} className="mb-3 rounded-lg border p-3"><p className="font-bold">{item.region}</p><p className="text-sm text-slate-500">${Number(item.revenue || 0).toLocaleString()} revenue | {Number(item.demand || 0).toLocaleString()} demand</p></div>)}</div>
        <div className="panel"><h2 className="section-title mb-4">Executive Alert Center</h2>{(data?.executive_alerts || []).map((item) => <p key={item.message} className="mb-3 rounded-lg bg-slate-50 p-3 text-sm dark:bg-white/5">{item.message}</p>)}</div>
      </section>
    </div>
  );
}
