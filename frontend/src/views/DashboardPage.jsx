import React from "react";
import { Activity, BarChart3, Boxes, DollarSign, Target } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import DatasetPicker from "../components/DatasetPicker";
import MetricCard from "../components/MetricCard";
import Skeleton from "../components/Skeleton";

const palette = ["#155e75", "#14b8a6", "#f59e0b", "#8b5cf6", "#ef4444"];

export default function DashboardPage({ datasets, selectedDatasetId, setSelectedDatasetId, analytics, loading, filters, setFilters, datasetFilters }) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="page-eyebrow">Executive dashboard</p><h2 className="page-title">Forecast intelligence center</h2></div>
        <DatasetPicker datasets={datasets} selectedDatasetId={selectedDatasetId} setSelectedDatasetId={setSelectedDatasetId} />
      </div>
      <div className="filter-bar">
        <input className="input" type="date" value={filters.start_date} onChange={(e) => setFilters({ ...filters, start_date: e.target.value })} />
        <input className="input" type="date" value={filters.end_date} onChange={(e) => setFilters({ ...filters, end_date: e.target.value })} />
        <select className="input" value={filters.category} onChange={(e) => setFilters({ ...filters, category: e.target.value })}><option value="">All categories</option>{datasetFilters.categories.map((item) => <option key={item}>{item}</option>)}</select>
        <select className="input" value={filters.region} onChange={(e) => setFilters({ ...filters, region: e.target.value })}><option value="">All regions</option>{datasetFilters.regions.map((item) => <option key={item}>{item}</option>)}</select>
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
          <div className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
            <Panel title="Sales Trend"><ResponsiveContainer width="100%" height={320}><AreaChart data={analytics.monthly_sales}><defs><linearGradient id="sales" x1="0" x2="0" y1="0" y2="1"><stop offset="5%" stopColor="#155e75" stopOpacity={0.38}/><stop offset="95%" stopColor="#155e75" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="#d8e3ea"/><XAxis dataKey="month"/><YAxis/><Tooltip/><Area type="monotone" dataKey="sales" stroke="#155e75" fill="url(#sales)" strokeWidth={3}/></AreaChart></ResponsiveContainer></Panel>
            <Panel title="Top Products"><ResponsiveContainer width="100%" height={320}><BarChart data={analytics.top_products}><CartesianGrid strokeDasharray="3 3" stroke="#d8e3ea"/><XAxis dataKey="product"/><YAxis/><Tooltip/><Bar dataKey="sales" radius={[8,8,0,0]}>{analytics.top_products.map((_, i) => <Cell key={i} fill={palette[i % palette.length]} />)}</Bar></BarChart></ResponsiveContainer></Panel>
          </div>
          <div className="grid gap-5 xl:grid-cols-2">
            <Panel title="Forecast Curve"><ResponsiveContainer width="100%" height={300}><LineChart data={analytics.forecast}><CartesianGrid strokeDasharray="3 3" stroke="#d8e3ea"/><XAxis dataKey="date"/><YAxis/><Tooltip/><Line dataKey="predicted_demand" stroke="#14b8a6" strokeWidth={3} dot={false}/><Line dataKey="upper_bound" stroke="#f59e0b" strokeDasharray="5 5" dot={false}/><Line dataKey="lower_bound" stroke="#8b5cf6" strokeDasharray="5 5" dot={false}/></LineChart></ResponsiveContainer></Panel>
            <Panel title="Recent Activities"><div className="space-y-3">{analytics.recent_activity.length === 0 ? <p className="empty">No recent activity yet.</p> : analytics.recent_activity.map((item) => <div key={item.id} className="activity-row"><BarChart3 size={18}/><div><p className="font-bold">{item.action}</p><p className="text-sm text-slate-500">{new Date(item.created_at).toLocaleString()}</p></div></div>)}</div></Panel>
          </div>
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
