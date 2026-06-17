import React, { useEffect, useState } from "react";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
import api from "../api/client";
import MetricCard from "../components/MetricCard";

export default function ApprovalsPage() {
  const [items, setItems] = useState([]);
  const load = async () => { const { data } = await api.get("/approvals"); setItems(data); };
  useEffect(() => { load(); }, []);
  const decide = async (id, status) => { await api.patch(`/approvals/${id}`, { status, decision_notes: `${status} from approval center` }); await load(); };
  const submitted = items.filter((item) => item.status === "submitted").length;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="Pending Review" value={submitted} icon={Clock} tone="amber" />
        <MetricCard title="Approved" value={items.filter((i) => i.status === "approved").length} icon={CheckCircle2} tone="mint" />
        <MetricCard title="Rejected" value={items.filter((i) => i.status === "rejected").length} icon={XCircle} tone="rose" />
      </div>
      <section className="panel">
        <h2 className="section-title mb-4">Forecast Approval Workflow</h2>
        <div className="overflow-auto">
          <table className="data-table">
            <thead><tr><th>Run</th><th>Organization</th><th>Status</th><th>Submitted By</th><th>Notes</th><th>Action</th></tr></thead>
            <tbody>{items.map((item) => <tr key={item.id}><td>#{item.run_id}</td><td>#{item.organization_id}</td><td><span className="status-pill">{item.status}</span></td><td>{item.submitted_by}</td><td>{item.notes || "Ready for governance review"}</td><td className="flex gap-2"><button className="secondary-button" onClick={() => decide(item.id, "approved")}>Approve</button><button className="danger-button" onClick={() => decide(item.id, "rejected")}>Reject</button></td></tr>)}</tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
