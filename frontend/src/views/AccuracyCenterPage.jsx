import React, { useEffect, useState } from "react";
import { Activity, Target, TrendingUp } from "lucide-react";
import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../api/client";
import DatasetPicker from "../components/DatasetPicker";
import MetricCard from "../components/MetricCard";
import DataTable from "../components/DataTable";

export default function AccuracyCenterPage({ datasets, selectedDatasetId, setSelectedDatasetId }) {
  const [data, setData] = useState(null);
  const [versions, setVersions] = useState([]);
  const [comparison, setComparison] = useState(null);
  useEffect(() => {
    if (!selectedDatasetId) return;
    Promise.all([api.get(`/accuracy-center/${selectedDatasetId}`), api.get(`/datasets/${selectedDatasetId}/versions`), api.get(`/datasets/${selectedDatasetId}/compare`)]).then(([a, v, c]) => { setData(a.data); setVersions(v.data); setComparison(c.data); });
  }, [selectedDatasetId]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="page-eyebrow">Forecast accuracy center</p><h2 className="page-title">Model performance dashboard</h2></div><DatasetPicker datasets={datasets} selectedDatasetId={selectedDatasetId} setSelectedDatasetId={setSelectedDatasetId}/></div>
      {!data ? <p className="empty">Select a dataset to review accuracy and versions.</p> : <>
        <div className="grid gap-4 md:grid-cols-3">
          <MetricCard icon={Activity} label="Forecast Runs" value={data.improvement_summary.run_count} trend="Historical evaluations"/>
          <MetricCard icon={TrendingUp} label="Accuracy Delta" value={`${data.improvement_summary.accuracy_delta}%`} trend="First to latest" tone="mint"/>
          <MetricCard icon={Target} label="Dataset Versions" value={versions.length} trend={`${comparison?.row_delta || 0} row delta`} tone="amber"/>
        </div>
        <section className="panel"><h3 className="mb-4 text-lg font-black">Accuracy trend</h3><ResponsiveContainer width="100%" height={300}><LineChart data={data.accuracy_trends}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="run_id"/><YAxis/><Tooltip/><Line dataKey="accuracy" stroke="#155e75" strokeWidth={3}/><Line dataKey="confidence_score" stroke="#14b8a6" strokeWidth={3}/></LineChart></ResponsiveContainer></section>
        <div className="grid gap-5 xl:grid-cols-2">
          <section className="panel"><h3 className="mb-4 text-lg font-black">Model evaluation report</h3><div className="space-y-3">{data.evaluation_report.map((item) => <p className="insight-row" key={item}>{item}</p>)}</div></section>
          <section className="panel"><h3 className="mb-4 text-lg font-black">Dataset versions</h3><DataTable columns={[{ key: "version", label: "Version" }, { key: "row_count", label: "Rows" }, { key: "change_summary", label: "Change" }, { key: "created_at", label: "Created", render: (row) => new Date(row.created_at).toLocaleString() }]} rows={versions}/></section>
        </div>
      </>}
    </div>
  );
}
