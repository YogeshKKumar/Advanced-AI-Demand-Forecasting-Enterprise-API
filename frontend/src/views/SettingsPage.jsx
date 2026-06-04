import React, { useEffect, useState } from "react";
import { BellRing, SlidersHorizontal, UserRound } from "lucide-react";
import api from "../api/client";
import DataTable from "../components/DataTable";
import { useAuth } from "../state/AuthContext";

export default function SettingsPage({ datasets }) {
  const { setUserFromProfile } = useAuth();
  const [profile, setProfile] = useState({ name: "", title: "", department: "", phone: "", preferences: {} });
  const [rules, setRules] = useState([]);
  const [widgets, setWidgets] = useState([]);
  const [rule, setRule] = useState({ dataset_id: "", name: "Low confidence alert", metric: "confidence_score", operator: "<", threshold: 70, channel: "in_app", is_active: true });

  const load = async () => {
    const [p, r, w] = await Promise.all([api.get("/profile"), api.get("/alerts/rules"), api.get("/dashboard/widgets")]);
    setProfile({ name: p.data.user.name, title: p.data.title, department: p.data.department, phone: p.data.phone, preferences: p.data.preferences });
    setRules(r.data);
    setWidgets(w.data);
  };
  useEffect(() => { load(); }, []);

  const saveProfile = async (event) => {
    event.preventDefault();
    const { data } = await api.patch("/profile", profile);
    setUserFromProfile?.(data.user);
    await load();
  };
  const saveRule = async (event) => {
    event.preventDefault();
    await api.post("/alerts/rules", { ...rule, dataset_id: rule.dataset_id ? Number(rule.dataset_id) : null, threshold: Number(rule.threshold) });
    await load();
  };
  const saveWidget = async (widget) => {
    await api.post("/dashboard/widgets", { ...widget, settings: widget.settings || {} });
    await load();
  };

  return (
    <div className="space-y-6">
      <div><p className="page-eyebrow">User management</p><h2 className="page-title">Profile, alerts and widgets</h2></div>
      <div className="grid gap-5 xl:grid-cols-2">
        <form onSubmit={saveProfile} className="panel space-y-3"><h3 className="flex items-center gap-2 text-lg font-black"><UserRound size={19}/>Profile management</h3><input className="input w-full" value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} placeholder="Name"/><input className="input w-full" value={profile.title} onChange={(e) => setProfile({ ...profile, title: e.target.value })} placeholder="Title"/><input className="input w-full" value={profile.department} onChange={(e) => setProfile({ ...profile, department: e.target.value })} placeholder="Department"/><input className="input w-full" value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} placeholder="Phone"/><button className="secondary-button">Update profile</button></form>
        <form onSubmit={saveRule} className="panel space-y-3"><h3 className="flex items-center gap-2 text-lg font-black"><BellRing size={19}/>Threshold alerts</h3><input className="input w-full" value={rule.name} onChange={(e) => setRule({ ...rule, name: e.target.value })}/><select className="input w-full" value={rule.dataset_id} onChange={(e) => setRule({ ...rule, dataset_id: e.target.value })}><option value="">All datasets</option>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}</select><select className="input w-full" value={rule.metric} onChange={(e) => setRule({ ...rule, metric: e.target.value })}><option value="accuracy">Accuracy</option><option value="confidence_score">Confidence</option><option value="low_stock">Low stock</option></select><input className="input w-full" type="number" value={rule.threshold} onChange={(e) => setRule({ ...rule, threshold: e.target.value })}/><button className="secondary-button">Create alert rule</button></form>
      </div>
      <section className="panel"><h3 className="mb-4 flex items-center gap-2 text-lg font-black"><SlidersHorizontal size={19}/>Dashboard widgets</h3><div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{widgets.map((widget) => <button key={widget.id} onClick={() => saveWidget({ ...widget, is_visible: !widget.is_visible })} className={`widget-tile ${widget.is_visible ? "widget-on" : ""}`}><b>{widget.title}</b><span>{widget.is_visible ? "Visible" : "Hidden"}</span></button>)}</div></section>
      <section className="panel"><h3 className="mb-4 text-lg font-black">Alert rules</h3><DataTable columns={[{ key: "name", label: "Name" }, { key: "metric", label: "Metric" }, { key: "threshold", label: "Threshold" }, { key: "channel", label: "Channel" }]} rows={rules}/></section>
    </div>
  );
}


