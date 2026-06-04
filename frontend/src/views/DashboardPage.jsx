import React from "react";
import { Activity, AlertTriangle, ArrowRight, BarChart3, Boxes, DollarSign, FileDown, RefreshCw, Sparkles, Target, TrendingUp, UploadCloud } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import DatasetPicker from "../components/DatasetPicker";
import MetricCard from "../components/MetricCard";
import Skeleton from "../components/Skeleton";

const palette = ["#155e75", "#14b8a6", "#f59e0b", "#8b5cf6", "#ef4444"];

export default function DashboardPage({ datasets, selectedDatasetId, setSelectedDatasetId, analytics, advancedAnalytics, liveSnapshot, liveMode, setLiveMode, autoForecast, setAutoForecast, canOperate, loading, filters, setFilters, datasetFilters, refresh, onNavigate }) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="page-eyebrow">Executive dashboard</p><h2 className="page-title">Forecast intelligence center</h2></div>
        <div className="flex flex-wrap items-center gap-2">
          <button className={`live-toggle ${liveMode ? "live-active" : ""}`} onClick={() => setLiveMode(!liveMode)}><span className="live-dot" />{liveMode ? "Live updates" : "Paused"}</button>
          {canOperate && <button className={`live-toggle ${autoForecast ? "live-active" : ""}`} onClick={() => setAutoForecast(!autoForecast)}><RefreshCw size={15}/>{autoForecast ? "Auto forecast" : "Auto forecast off"}</button>}
          <button className="icon-button" onClick={refresh} title="Refresh dashboard"><RefreshCw size={18}/></button>
          <DatasetPicker datasets={datasets} selectedDatasetId={selectedDatasetId} setSelectedDatasetId={setSelectedDatasetId} />
        </div>
      </div>
      <div className="filter-bar">
        <input className="input" type="date" value={filters.start_date} onChange={(e) => setFilters({ ...filters, start_date: e.target.value })} />
        <input className="input" type="date" value={filters.end_date} onChange={(e) => setFilters({ ...filters, end_date: e.target.value })} />
        <select className="input" value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })}><option value="">All categories</option>{datasetFilters.categories.map((item) => <option key={item}>{item}</option>)}</select>
        <select className="input" value={filters.region} onChange={(e) => setFilters({ ...filters, region: e.target.value })}><option value="">All regions</option>{datasetFilters.regions.map((item) => <option key={item}>{item}</option>)}</select>
      </div>
      <div className="workflow-bar">
        <div>
          <p className="text-xs font-black uppercase text-slate-400">Workflow</p>
          <p className="mt-1 font-black">Move from data to decisions</p>
        </div>
        {canOperate && <QuickAction icon={UploadCloud} label="Import Sales" onClick={() => onNavigate("upload")} />}
        {canOperate && <QuickAction icon={TrendingUp} label="Run Forecast" onClick={() => onNavigate("forecast")} />}
        <QuickAction icon={Sparkles} label="View Intelligence" onClick={() => onNavigate("insights")} />
        <QuickAction icon={FileDown} label="Export Reports" onClick={() => onNavigate("reports")} />
      </div>
      {!selectedDatasetId && <EmptyState />}
      {loading && <div className="grid gap-4 md:grid-cols-4"><Skeleton /><Skeleton /><Skeleton /><Skeleton /></div>}
      {analytics && !loading && (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard icon={DollarSign} label="Total Sales" value={`$${Number(analytics.total_sales).toLocaleString()}`} trend="Live filtered revenue" />
            <MetricCard icon={Boxes} label="Units Sold" value={Number(analytics.total_units).toLocaleString()} trend="Demand volume" tone="mint" />
            <MetricCard icon={Target} label="Accuracy" value={`${analytics.forecast_accuracy}%`} trend="Latest model score" tone="amber" />
            <MetricCard icon={Activity} label="Confidence" value={`${analytics.confidence_score}%`} trend="Prediction reliability" />
          </div>
          {advancedAnalytics && (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard icon={TrendingUp} label="Predicted Revenue" value={`$${Number(advancedAnalytics.revenue_prediction).toLocaleString()}`} trend="Forward revenue outlook" tone="mint" />
              <MetricCard icon={Boxes} label="Predicted Units" value={Number(advancedAnalytics.predicted_units).toLocaleString()} trend="Expected demand volume" />
              <MetricCard icon={AlertTriangle} label="Anomalies" value={advancedAnalytics.anomalies.length} trend="Unusual sales patterns" tone="amber" />
              <MetricCard icon={Activity} label="Live Sales Window" value={`$${Number(liveSnapshot?.rolling_sales || 0).toLocaleString()}`} trend="Most recent activity" />
            </div>
          )}
          <div className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
            <Panel title="Sales Trend"><ResponsiveContainer width="100%" height={320}><AreaChart data={analytics.monthly_sales}><defs><linearGradient id="sales" x1="0" x2="0" y1="0" y2="1"><stop offset="5%" stopColor="#155e75" stopOpacity={0.38}/><stop offset="95%" stopColor="#155e75" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="#d8e3ea"/><XAxis dataKey="month"/><YAxis/><Tooltip/><Area type="monotone" dataKey="sales" stroke="#155e75" fill="url(#sales)" strokeWidth={3}/></AreaChart></ResponsiveContainer></Panel>
            <Panel title="Top Products"><ResponsiveContainer width="100%" height={320}><BarChart data={analytics.top_products}><CartesianGrid strokeDasharray="3 3" stroke="#d8e3ea"/><XAxis dataKey="product"/><YAxis/><Tooltip/><Bar dataKey="sales" radius={[8,8,0,0]}>{analytics.top_products.map((_, i) => <Cell key={i} fill={palette[i % palette.length]} />)}</Bar></BarChart></ResponsiveContainer></Panel>
          </div>
          <div className="grid gap-5 xl:grid-cols-2">
            <Panel title="Forecast Curve"><ResponsiveContainer width="100%" height={300}><LineChart data={analytics.forecast}><CartesianGrid strokeDasharray="3 3" stroke="#d8e3ea"/><XAxis dataKey="date"/><YAxis/><Tooltip/><Line dataKey="predicted_demand" stroke="#14b8a6" strokeWidth={3} dot={false}/><Line dataKey="upper_bound" stroke="#f59e0b" strokeDasharray="5 5" dot={false}/><Line dataKey="lower_bound" stroke="#8b5cf6" strokeDasharray="5 5" dot={false}/></LineChart></ResponsiveContainer></Panel>
            <Panel title="Recent Activities"><div className="space-y-3">{analytics.recent_activity.length === 0 ? <p className="empty">No recent activity yet.</p> : analytics.recent_activity.map((item) => <div key={item.id} className="activity-row"><BarChart3 size={18}/><div><p className="font-bold">{item.action}</p><p className="text-sm text-slate-500">{new Date(item.created_at).toLocaleString()}</p></div></div>)}</div></Panel>
          </div>
          {advancedAnalytics && (
            <>
              <div className="grid gap-5 xl:grid-cols-2">
                <Panel title="Region Revenue Forecast"><ResponsiveContainer width="100%" height={285}><BarChart data={advancedAnalytics.region_forecasts}><CartesianGrid strokeDasharray="3 3" stroke="#d8e3ea"/><XAxis dataKey="region"/><YAxis/><Tooltip/><Bar dataKey="predicted_revenue" fill="#155e75" radius={[8,8,0,0]}/></BarChart></ResponsiveContainer></Panel>
                <Panel title="Category Sales Insights"><ResponsiveContainer width="100%" height={285}><BarChart data={advancedAnalytics.category_insights}><CartesianGrid strokeDasharray="3 3" stroke="#d8e3ea"/><XAxis dataKey="category"/><YAxis/><Tooltip/><Bar dataKey="sales" fill="#14b8a6" radius={[8,8,0,0]}/></BarChart></ResponsiveContainer></Panel>
              </div>
              <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
                <Panel title="Inventory Risk Analysis">
                  <div className="space-y-2">{advancedAnalytics.inventory_risk.map((item) => <div key={item.product} className="risk-row"><span className={`risk-pill risk-${item.risk}`}>{item.risk}</span><b>{item.product}</b><span className="ml-auto text-sm text-slate-500">Coverage {item.coverage_ratio}x</span></div>)}</div>
                </Panel>
                <Panel title="AI Business Insights">
                  <div className="space-y-3">{advancedAnalytics.generated_insights.map((item) => <div className="insight-row" key={item}><Sparkles size={17} className="shrink-0 text-mint"/><p>{item}</p></div>)}</div>
                </Panel>
              </div>
              <Panel title="Real-Time Sales Monitoring">
                {liveSnapshot?.latest_sales?.length ? <div className="overflow-auto"><table className="data-table"><thead><tr><th>Date</th><th>Product</th><th>Region</th><th>Units</th><th>Sales</th></tr></thead><tbody>{liveSnapshot.latest_sales.slice(0, 8).map((item, index) => <tr key={`${item.product}-${item.date}-${index}`}><td>{item.date}</td><td>{item.product}</td><td>{item.region}</td><td>{item.quantity}</td><td>${Number(item.sales).toLocaleString()}</td></tr>)}</tbody></table></div> : <p className="empty">No live sales records available.</p>}
              </Panel>
            </>
          )}
        </>
      )}
    </div>
  );
}

function Panel({ title, children }) {
  return <section className="panel"><h3 className="mb-4 text-lg font-black">{title}</h3>{children}</section>;
}

function EmptyState() {
  return <div className="rounded-lg border border-dashed border-slate-300 p-12 text-center dark:border-white/10"><p className="text-xl font-black">Upload a dataset to unlock the dashboard.</p><p className="mt-2 text-slate-500">CSV and Excel files with date, product, quantity, and sales are supported.</p></div>;
}

function QuickAction({ icon: Icon, label, onClick }) {
  return <button className="quick-action" onClick={onClick}><Icon size={18}/><span>{label}</span><ArrowRight size={15}/></button>;
}


