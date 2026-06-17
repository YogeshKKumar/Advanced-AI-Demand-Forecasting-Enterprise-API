import React, { useEffect, useState } from "react";
import { Bell, Mail, Megaphone } from "lucide-react";
import api from "../api/client";
import MetricCard from "../components/MetricCard";

export default function NotificationCenterPage() {
  const [preferences, setPreferences] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [form, setForm] = useState({ organization_id: "", event_type: "forecast.approved", channel: "in_app", is_enabled: true });
  const load = async () => { const [prefs, orgs] = await Promise.all([api.get("/notification-preferences"), api.get("/organizations")]); setPreferences(prefs.data); setOrganizations(orgs.data); };
  useEffect(() => { load(); }, []);
  const save = async (event) => {
    event.preventDefault();
    await api.post("/notification-preferences", { ...form, organization_id: form.organization_id ? Number(form.organization_id) : null });
    await load();
  };
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="Preferences" value={preferences.length} icon={Bell} tone="ocean" />
        <MetricCard title="Email Hooks" value={preferences.filter((item) => item.channel === "email").length} icon={Mail} tone="mint" />
        <MetricCard title="Announcements" value={organizations.length} icon={Megaphone} tone="amber" />
      </div>
      <section className="panel">
        <h2 className="section-title mb-4">Notification Center</h2>
        <form onSubmit={save} className="grid gap-3 md:grid-cols-5">
          <select className="input" value={form.organization_id} onChange={(e) => setForm({ ...form, organization_id: e.target.value })}><option value="">All organizations</option>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
          <input className="input" value={form.event_type} onChange={(e) => setForm({ ...form, event_type: e.target.value })} />
          <select className="input" value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value })}><option value="in_app">In-app</option><option value="email">Email</option></select>
          <label className="flex items-center gap-2 rounded-lg border px-3"><input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })} /> Enabled</label>
          <button className="primary-button" type="submit">Save</button>
        </form>
      </section>
      <section className="panel overflow-auto">
        <table className="data-table"><thead><tr><th>Event</th><th>Channel</th><th>Status</th><th>Organization</th></tr></thead><tbody>{preferences.map((item) => <tr key={item.id}><td>{item.event_type}</td><td>{item.channel}</td><td>{item.is_enabled ? "Enabled" : "Disabled"}</td><td>{item.organization_id || "All"}</td></tr>)}</tbody></table>
      </section>
    </div>
  );
}
