import React, { useEffect, useState } from "react";
import { PlugZap, RadioTower } from "lucide-react";
import api from "../api/client";
import DataTable from "../components/DataTable";

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState([]);
  const [webhooks, setWebhooks] = useState([]);
  const [integration, setIntegration] = useState({ name: "Inventory connector", provider: "inventory", base_url: "", auth_type: "api_key", secret_ref: "" });
  const [webhook, setWebhook] = useState({ name: "Forecast completed hook", url: "https://example.com/webhook", event_type: "forecast.completed", secret: "", is_active: true });

  const load = async () => {
    const [i, w] = await Promise.all([api.get("/integrations"), api.get("/webhooks")]);
    setIntegrations(i.data);
    setWebhooks(w.data);
  };
  useEffect(() => { load(); }, []);

  const saveIntegration = async (event) => {
    event.preventDefault();
    await api.post("/integrations", { ...integration, settings: {} });
    await load();
  };

  const saveWebhook = async (event) => {
    event.preventDefault();
    await api.post("/webhooks", webhook);
    await load();
  };

  return (
    <div className="space-y-6">
      <div><p className="page-eyebrow">Enterprise integrations</p><h2 className="page-title">ERP, inventory, APIs and webhooks</h2></div>
      <div className="grid gap-5 xl:grid-cols-2">
        <form onSubmit={saveIntegration} className="panel space-y-3"><h3 className="flex items-center gap-2 text-lg font-black"><PlugZap size={19}/>Integration settings</h3><input className="input w-full" value={integration.name} onChange={(e) => setIntegration({ ...integration, name: e.target.value })}/><select className="input w-full" value={integration.provider} onChange={(e) => setIntegration({ ...integration, provider: e.target.value })}><option value="inventory">Inventory</option><option value="erp">ERP</option><option value="external_api">External API</option></select><input className="input w-full" placeholder="Base URL" value={integration.base_url} onChange={(e) => setIntegration({ ...integration, base_url: e.target.value })}/><input className="input w-full" placeholder="Secret reference" value={integration.secret_ref} onChange={(e) => setIntegration({ ...integration, secret_ref: e.target.value })}/><button className="secondary-button">Save integration</button></form>
        <form onSubmit={saveWebhook} className="panel space-y-3"><h3 className="flex items-center gap-2 text-lg font-black"><RadioTower size={19}/>Webhook support</h3><input className="input w-full" value={webhook.name} onChange={(e) => setWebhook({ ...webhook, name: e.target.value })}/><input className="input w-full" value={webhook.url} onChange={(e) => setWebhook({ ...webhook, url: e.target.value })}/><input className="input w-full" value={webhook.event_type} onChange={(e) => setWebhook({ ...webhook, event_type: e.target.value })}/><button className="secondary-button">Save webhook</button></form>
      </div>
      <section className="panel"><h3 className="mb-4 text-lg font-black">Managed integrations</h3><DataTable columns={[{ key: "name", label: "Name" }, { key: "provider", label: "Provider" }, { key: "status", label: "Status" }, { key: "base_url", label: "Endpoint" }]} rows={integrations}/></section>
      <section className="panel"><h3 className="mb-4 text-lg font-black">Webhook subscriptions</h3><DataTable columns={[{ key: "name", label: "Name" }, { key: "event_type", label: "Event" }, { key: "url", label: "URL" }, { key: "is_active", label: "Active", render: (row) => row.is_active ? "Yes" : "No" }]} rows={webhooks}/></section>
    </div>
  );
}


