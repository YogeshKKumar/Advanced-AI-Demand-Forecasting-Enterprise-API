import React, { useEffect, useState } from "react";
import { Database, Shield, Users, Workflow } from "lucide-react";
import api from "../api/client";
import MetricCard from "../components/MetricCard";

export default function AdminPage() {
  const [summary, setSummary] = useState(null);
  const [users, setUsers] = useState([]);
  const [datasets, setDatasets] = useState([]);

  useEffect(() => {
    Promise.all([api.get("/admin/summary"), api.get("/admin/users"), api.get("/admin/datasets")]).then(([s, u, d]) => {
      setSummary(s.data);
      setUsers(u.data);
      setDatasets(d.data.items || []);
    });
  }, []);

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
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="panel"><h3 className="mb-4 text-lg font-black">Users</h3><table className="data-table"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td>{user.name}</td><td>{user.email}</td><td>{user.role}</td><td>{user.is_active ? "Active" : "Disabled"}</td></tr>)}</tbody></table></section>
        <section className="panel"><h3 className="mb-4 text-lg font-black">Datasets</h3><table className="data-table"><thead><tr><th>Name</th><th>Owner</th><th>Rows</th><th>Status</th></tr></thead><tbody>{datasets.map((dataset) => <tr key={dataset.id}><td>{dataset.name}</td><td>{dataset.owner}</td><td>{dataset.row_count}</td><td>{dataset.status}</td></tr>)}</tbody></table></section>
      </div>
    </div>
  );
}
