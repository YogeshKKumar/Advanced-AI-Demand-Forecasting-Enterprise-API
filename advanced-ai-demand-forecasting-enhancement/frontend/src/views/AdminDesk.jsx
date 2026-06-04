import React, { useEffect, useState } from "react";
import { Bell, Database, FileStack, Users } from "lucide-react";
import gateway from "../services/gateway";
import FigureTile from "../widgets/FigureTile";

export default function AdminDesk() {
  const [overview, setOverview] = useState(null);

  useEffect(() => {
    gateway.get("/admin/overview").then(({ data }) => setOverview(data));
  }, []);

  if (!overview) return <p className="soft-empty animate-pulse">Loading admin overview...</p>;

  return (
    <div className="space-y-6">
      <div><p className="section-label">Admin desk</p><h2 className="section-title">Platform control overview</h2></div>
      <div className="grid gap-4 md:grid-cols-4">
        <FigureTile icon={Users} label="Accounts" value={overview.accounts} />
        <FigureTile icon={Database} label="Workbooks" value={overview.workbooks} />
        <FigureTile icon={FileStack} label="Scenarios" value={overview.scenarios} />
        <FigureTile icon={Bell} label="Alerts" value={overview.alerts} />
      </div>
      <section className="surface">
        <h3 className="mb-4 text-lg font-black">Recent events</h3>
        <div className="space-y-3">{overview.recent_events.map((item, index) => <div className="event-row" key={index}><b>{item.event_name}</b><span>{item.reference}</span><span>{new Date(item.created_at).toLocaleString()}</span></div>)}</div>
      </section>
    </div>
  );
}
