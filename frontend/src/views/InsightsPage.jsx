import React, { useMemo, useState } from "react";
import { AlertTriangle, ArrowUpRight, Boxes, MapPinned, RefreshCw, Sparkles, TrendingUp } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import DatasetPicker from "../components/DatasetPicker";
import MetricCard from "../components/MetricCard";
import Skeleton from "../components/Skeleton";

const riskColors = { high: "#ef4444", medium: "#f59e0b", low: "#14b8a6" };

export default function InsightsPage({ datasets, selectedDatasetId, setSelectedDatasetId, advancedAnalytics, liveSnapshot, loading, refresh }) {
  const [riskFilter, setRiskFilter] = useState("all");
  const [regionSort, setRegionSort] = useState("revenue");
  const risks = useMemo(() => {
    const items = advancedAnalytics?.inventory_risk || [];
    return riskFilter === "all" ? items : items.filter((item) => item.risk === riskFilter);
  }, [advancedAnalytics, riskFilter]);
  const regions = useMemo(() => {
    const items = [...(advancedAnalytics?.region_forecasts || [])];
    return items.sort((a, b) => regionSort === "share" ? b.share_percent - a.share_percent : b.predicted_revenue - a.predicted_revenue);
  }, [advancedAnalytics, regionSort]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="page-eyebrow">Decision intelligence</p><h2 className="page-title">AI insight workspace</h2></div>
        <div className="flex items-center gap-2">
          <button className="icon-button" onClick={refresh} title="Refresh intelligence"><RefreshCw size={18}/></button>
          <DatasetPicker datasets={datasets} selectedDatasetId={selectedDatasetId} setSelectedDatasetId={setSelectedDatasetId} />
        </div>
      </div>
      {!selectedDatasetId && <p className="empty">Select a dataset to view business intelligence.</p>}
      {loading && <div className="grid gap-4 md:grid-cols-4"><Skeleton /><Skeleton /><Skeleton /><Skeleton /></div>}
      {advancedAnalytics && !loading && (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard icon={TrendingUp} label="Revenue Outlook" value={`$${Number(advancedAnalytics.revenue_prediction).toLocaleString()}`} trend="Projected revenue" tone="mint" />
            <MetricCard icon={Boxes} label="Future Demand" value={Number(advancedAnalytics.predicted_units).toLocaleString()} trend="Forecast units" />
            <MetricCard icon={AlertTriangle} label="Signals Found" value={advancedAnalytics.anomalies.length} trend="Anomalies flagged" tone="amber" />
            <MetricCard icon={MapPinned} label="Sales Window" value={`$${Number(liveSnapshot?.rolling_sales || 0).toLocaleString()}`} trend="Recent live sales" />
          </div>
          <section className="insight-hero">
            <div className="flex items-center gap-2"><Sparkles size={20}/><h3 className="text-lg font-black">Executive AI Brief</h3></div>
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              {advancedAnalytics.generated_insights.map((message) => <p className="brief-item" key={message}>{message}</p>)}
            </div>
          </section>
          <div className="grid gap-5 xl:grid-cols-2">
            <section className="panel">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-lg font-black">Regional Opportunity</h3>
                <select className="compact-select" value={regionSort} onChange={(event) => setRegionSort(event.target.value)}><option value="revenue">Sort by revenue</option><option value="share">Sort by share</option></select>
              </div>
              <ResponsiveContainer width="100%" height={255}><BarChart data={regions}><CartesianGrid strokeDasharray="3 3" stroke="#d8e3ea"/><XAxis dataKey="region"/><YAxis/><Tooltip/><Bar dataKey="predicted_revenue" fill="#155e75" radius={[8,8,0,0]}/></BarChart></ResponsiveContainer>
              <div className="mt-3 space-y-2">{regions.slice(0, 3).map((item) => <div className="rank-row" key={item.region}><b>{item.region}</b><span>{item.share_percent}% share</span><strong>${Number(item.predicted_revenue).toLocaleString()}</strong></div>)}</div>
            </section>
            <section className="panel">
              <h3 className="mb-4 text-lg font-black">Category Portfolio</h3>
              <ResponsiveContainer width="100%" height={255}><BarChart data={advancedAnalytics.category_insights}><CartesianGrid strokeDasharray="3 3" stroke="#d8e3ea"/><XAxis dataKey="category"/><YAxis/><Tooltip/><Bar dataKey="sales" radius={[8,8,0,0]}>{advancedAnalytics.category_insights.map((_, index) => <Cell fill={["#14b8a6", "#155e75", "#f59e0b", "#8b5cf6"][index % 4]} key={index}/>)}</Bar></BarChart></ResponsiveContainer>
              <div className="mt-3 flex flex-wrap gap-2">{advancedAnalytics.category_insights.map((item) => <span className="tag" key={item.category}>{item.category}: {item.revenue_share}%</span>)}</div>
            </section>
          </div>
          <section className="panel">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-lg font-black">Inventory Risk Board</h3>
              <div className="segmented">{["all", "high", "medium", "low"].map((level) => <button className={riskFilter === level ? "segment-active" : ""} onClick={() => setRiskFilter(level)} key={level}>{level}</button>)}</div>
            </div>
            <div className="grid gap-3 lg:grid-cols-2">{risks.length ? risks.map((item) => <div className="inventory-item" key={item.product}><div className={`risk-ring risk-${item.risk}`}><span>{item.coverage_ratio}x</span></div><div><p className="font-black">{item.product}</p><p className="text-sm text-slate-500">{item.forecast_units} forecast units</p></div><span className={`risk-pill risk-${item.risk}`}>{item.risk}</span></div>) : <p className="empty lg:col-span-2">No matching inventory risks.</p>}</div>
          </section>
          <div className="grid gap-5 xl:grid-cols-2">
            <section className="panel"><h3 className="mb-4 text-lg font-black">Anomaly Review Queue</h3>{advancedAnalytics.anomalies.length ? <div className="space-y-2">{advancedAnalytics.anomalies.map((item) => <div className="alert-record" key={`${item.product}-${item.date}`}><AlertTriangle size={18} color={riskColors[item.severity] || riskColors.medium}/><div><b>{item.product}</b><p>{item.date} - observed {item.observed_quantity}, expected {item.expected_quantity}</p></div><strong>{item.deviation_percent}%</strong></div>)}</div> : <p className="empty">No unusual sales patterns require review.</p>}</section>
            <section className="panel"><h3 className="mb-4 text-lg font-black">Seasonal Opportunities</h3><div className="space-y-2">{advancedAnalytics.seasonal_trends.map((item) => <div className="season-row" key={item.month}><span>{item.month}</span><div className="season-bar"><i style={{ width: `${Math.max(8, Math.min(100, Math.abs(item.trend_percent) + 24))}%` }} /></div><b>{item.trend_percent > 0 ? "+" : ""}{item.trend_percent}%</b><ArrowUpRight size={15} className={item.signal === "peak" ? "text-mint" : "text-slate-400"}/></div>)}</div></section>
          </div>
        </>
      )}
    </div>
  );
}
