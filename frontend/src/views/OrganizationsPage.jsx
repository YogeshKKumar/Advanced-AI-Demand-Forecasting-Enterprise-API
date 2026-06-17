import React, { useEffect, useState } from "react";
import { Building2, Database, Plus, Users } from "lucide-react";
import api from "../api/client";
import MetricCard from "../components/MetricCard";

export default function OrganizationsPage({ datasets }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ name: "Retail Enterprise Group", industry: "Retail", region: "Global", status: "active" });
  const [selectedOrg, setSelectedOrg] = useState("");
  const [datasetId, setDatasetId] = useState("");

  const load = async () => {
    const { data } = await api.get("/organizations");
    setItems(data);
    if (!selectedOrg && data[0]) setSelectedOrg(String(data[0].id));
  };

  useEffect(() => { load(); }, []);

  const create = async (event) => {
    event.preventDefault();
    await api.post("/organizations", form);
    await load();
  };

  const attachDataset = async () => {
    if (!selectedOrg || !datasetId) return;
    await api.post(`/organizations/${selectedOrg}/datasets`, { dataset_id: Number(datasetId) });
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="Organizations" value={items.length} icon={Building2} tone="ocean" />
        <MetricCard title="Datasets Assigned" value={items.reduce((sum, item) => sum + item.dataset_count, 0)} icon={Database} tone="mint" />
        <MetricCard title="Forecast Runs" value={items.reduce((sum, item) => sum + item.forecast_count, 0)} icon={Users} tone="amber" />
      </div>
      <section className="panel">
        <div className="mb-4 flex items-center justify-between"><h2 className="section-title">Organization Management</h2><Building2 /></div>
        <form onSubmit={create} className="grid gap-3 md:grid-cols-5">
          <input className="input md:col-span-2" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Organization name" />
          <input className="input" value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} placeholder="Industry" />
          <input className="input" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} placeholder="Region" />
          <button className="primary-button" type="submit"><Plus size={16} /> Create</button>
        </form>
      </section>
      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="panel overflow-hidden">
          <h3 className="section-title mb-4">Enterprise Organizations</h3>
          <div className="overflow-auto">
            <table className="data-table">
              <thead><tr><th>Name</th><th>Industry</th><th>Region</th><th>Members</th><th>Datasets</th><th>Forecasts</th></tr></thead>
              <tbody>{items.map((item) => <tr key={item.id}><td className="font-bold">{item.name}</td><td>{item.industry}</td><td>{item.region}</td><td>{item.member_count}</td><td>{item.dataset_count}</td><td>{item.forecast_count}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
        <div className="panel">
          <h3 className="section-title mb-4">Attach Dataset</h3>
          <select className="input mb-3" value={selectedOrg} onChange={(e) => setSelectedOrg(e.target.value)}>{items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
          <select className="input mb-3" value={datasetId} onChange={(e) => setDatasetId(e.target.value)}><option value="">Select dataset</option>{datasets.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
          <button className="secondary-button w-full" onClick={attachDataset}>Attach Dataset</button>
        </div>
      </section>
    </div>
  );
}
