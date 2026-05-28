import React, { useEffect, useState } from "react";
import { Activity, Database, Shield, Timer, Users, Workflow } from "lucide-react";
import api from "../api/client";
import MetricCard from "../components/MetricCard";

export default function AdminPage() {
  const [summary, setSummary] = useState(null);
  const [users, setUsers] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [userSearch, setUserSearch] = useState("");

  const load = (search = "") => {
    Promise.all([api.get("/admin/summary"), api.get(`/admin/users?search=${encodeURIComponent(search)}`), api.get("/admin/datasets"), api.get("/monitoring/metrics")]).then(([s, u, d, m]) => {
      setSummary(s.data);
      setUsers(u.data);
      setDatasets(d.data.items || []);
      setMetrics(m.data);
    });
  };

  useEffect(() => { load(); }, []);

  const setRole = async (id, role) => {
    await api.patch(`/admin/users/${id}/role`, { role });
    load(userSearch);
  };

  if (!summary) return <div className="panel animate-pulse">Loading admin workspace...</div>;

  return (
    <div className="space-y-6">
      <div><p className="page-eyebrow">Admin management</p><h2 className="page-title">Enterprise control panel</h2></div>
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard icon={Users} label="Users" value={summary.total_users} trend={`${summary.active_users} active`} />
        <MetricCard icon={Database} label="Datasets" value={summary.total_datasets} trend={`${summary.total_records} records`} tone="mint" />
        <MetricCard icon={Workflow} label="Forecast Runs" value={summary.total_forecast_runs} trend="AI jobs completed" tone="amber" />
        <MetricCard icon={Shield} label="Reports" value={summary.total_reports} trend="Exports generated" />
      </div>
      {metrics && <div className="grid gap-4 md:grid-cols-4">
        <MetricCard icon={Activity} label="API Requests / Hour" value={metrics.requests_last_hour} trend="Tracked endpoints" tone="mint" />
        <MetricCard icon={Timer} label="Average Latency" value={`${metrics.average_duration_ms} ms`} trend="API performance" />
        <MetricCard icon={Shield} label="Error Rate" value={`${metrics.error_rate}%`} trend="Operational health" tone="amber" />
        <MetricCard icon={Workflow} label="Retraining Jobs" value={metrics.retraining_jobs} trend="Optimization history" />
      </div>}
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="panel"><div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h3 className="text-lg font-black">Users and Roles</h3><form onSubmit={(event) => { event.preventDefault(); load(userSearch); }}><input className="input h-10" placeholder="Search users" value={userSearch} onChange={(event) => setUserSearch(event.target.value)} /></form></div><table className="data-table"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td>{user.name}</td><td>{user.email}</td><td><select className="compact-select" value={user.role === "admin" ? "super_admin" : user.role} onChange={(event) => setRole(user.id, event.target.value)}><option value="super_admin">Super Admin</option><option value="analyst">Analyst</option><option value="viewer">Viewer</option></select></td><td>{user.is_active ? "Active" : "Disabled"}</td></tr>)}</tbody></table></section>
        <section className="panel"><h3 className="mb-4 text-lg font-black">Datasets</h3><table className="data-table"><thead><tr><th>Name</th><th>Owner</th><th>Rows</th><th>Status</th></tr></thead><tbody>{datasets.map((dataset) => <tr key={dataset.id}><td>{dataset.name}</td><td>{dataset.owner}</td><td>{dataset.row_count}</td><td>{dataset.status}</td></tr>)}</tbody></table></section>
      </div>
      {metrics && <section className="panel"><h3 className="mb-4 text-lg font-black">Endpoint Performance</h3><div className="grid gap-3 md:grid-cols-3">{metrics.slowest_endpoints.map((item) => <div className="activity-row" key={item.endpoint}><div><p className="font-bold">{item.endpoint}</p><p className="text-sm text-slate-500">{item.average_ms} ms average - {item.calls} calls</p></div></div>)}</div></section>}
    </div>
  );
}
