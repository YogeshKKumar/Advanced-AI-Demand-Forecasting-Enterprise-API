import React, { useState } from "react";
import { Download, FileSpreadsheet, FileText, GitCompareArrows, Sparkles } from "lucide-react";
import api from "../api/client";
import DatasetPicker from "../components/DatasetPicker";

export default function ReportsPage({ datasets, selectedDatasetId, setSelectedDatasetId, refresh }) {
  const [summary, setSummary] = useState(null);
  const [advanced, setAdvanced] = useState(null);
  const [comparison, setComparison] = useState([]);
  const [modelFilter, setModelFilter] = useState("");

  const loadSummary = async () => {
    if (!selectedDatasetId) return;
    const [summaryResponse, advancedResponse, comparisonResponse] = await Promise.all([
      api.get(`/reports/${selectedDatasetId}/summary`),
      api.get(`/analytics/${selectedDatasetId}/advanced`),
      api.get(`/forecast/${selectedDatasetId}/compare`)
    ]);
    setSummary(summaryResponse.data);
    setAdvanced(advancedResponse.data);
    setComparison(comparisonResponse.data);
  };

  const downloadComparison = async () => {
    if (!selectedDatasetId) return;
    const { data } = await api.get(`/reports/${selectedDatasetId}/comparison/excel`, { responseType: "blob" });
    const url = URL.createObjectURL(data);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "forecast-model-comparison.xlsx";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const download = async (type) => {
    if (!selectedDatasetId) return;
    const { data } = await api.get(`/reports/${selectedDatasetId}/${type}`, { responseType: "blob" });
    const url = URL.createObjectURL(data);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `enterprise-demand-report.${type === "excel" ? "xlsx" : "pdf"}`;
    anchor.click();
    URL.revokeObjectURL(url);
    await refresh?.();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="page-eyebrow">Export center</p><h2 className="page-title">Reports and documentation</h2></div>
        <DatasetPicker datasets={datasets} selectedDatasetId={selectedDatasetId} setSelectedDatasetId={setSelectedDatasetId} />
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        <button onClick={() => download("excel")} className="report-action"><FileSpreadsheet size={34}/><span>Export Excel Workbook</span><Download size={20}/></button>
        <button onClick={() => download("pdf")} className="report-action"><FileText size={34}/><span>Export Branded PDF</span><Download size={20}/></button>
        <button onClick={downloadComparison} className="report-action"><GitCompareArrows size={34}/><span>Comparison Workbook</span><Download size={20}/></button>
      </div>
      <section className="panel">
        <div className="mb-4 flex items-center justify-between"><h3 className="text-lg font-black">Report preview</h3><button onClick={loadSummary} className="secondary-button">Refresh Preview</button></div>
        {!summary ? <p className="empty">Select a dataset and refresh preview.</p> : <div className="grid gap-4 md:grid-cols-4"><Preview label="Rows" value={summary.dataset.row_count}/><Preview label="Model" value={summary.latest_run?.model_name || "Pending"}/><Preview label="Accuracy" value={`${summary.latest_run?.accuracy || 0}%`}/><Preview label="Forecast Points" value={summary.forecast.length}/></div>}
      </section>
      {advanced && <section className="panel"><h3 className="mb-4 flex items-center gap-2 text-lg font-black"><Sparkles size={19} className="text-mint"/> AI-Generated Business Summary</h3><div className="grid gap-3 lg:grid-cols-2">{advanced.generated_insights.map((item) => <p className="insight-row" key={item}>{item}</p>)}</div></section>}
      {comparison.length > 0 && <section className="panel">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h3 className="text-lg font-black">Forecast Comparison Report</h3><input className="input h-10" placeholder="Filter model" value={modelFilter} onChange={(event) => setModelFilter(event.target.value)} /></div>
        <div className="overflow-auto"><table className="data-table"><thead><tr><th>Model</th><th>Accuracy</th><th>RMSE</th><th>MAE</th><th>Confidence</th></tr></thead><tbody>{comparison.filter((item) => item.model_name.toLowerCase().includes(modelFilter.toLowerCase())).map((item) => <tr key={item.model_name}><td>{item.model_name}</td><td>{item.average_accuracy}%</td><td>{item.average_rmse}</td><td>{item.average_mae}</td><td>{item.confidence_score}%</td></tr>)}</tbody></table></div>
      </section>}
    </div>
  );
}

function Preview({ label, value }) {
  return <div className="rounded-lg bg-slate-100 p-4 dark:bg-white/10"><p className="text-sm text-slate-500">{label}</p><p className="mt-1 text-2xl font-black">{value}</p></div>;
}


