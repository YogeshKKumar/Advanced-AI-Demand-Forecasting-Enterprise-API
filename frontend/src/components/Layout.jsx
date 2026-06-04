import React, { useEffect, useState } from "react";
import { BarChart3, Bell, CalendarClock, Database, FileText, LineChart, LogOut, Moon, PlugZap, Search, Settings, Shield, Sparkles, Sun, UploadCloud } from "lucide-react";
import api from "../api/client";
import { useAuth } from "../state/AuthContext";

const nav = [
  { id: "dashboard", label: "Dashboard", icon: BarChart3 },
  { id: "insights", label: "Intelligence", icon: Sparkles },
  { id: "upload", label: "Upload", icon: UploadCloud },
  { id: "forecast", label: "Forecast", icon: LineChart },
  { id: "reports", label: "Reports", icon: FileText },
  { id: "automation", label: "Automation", icon: CalendarClock }
];

export default function Layout({ activePage, setActivePage, notifications, refreshNotifications, children }) {
  const { user, logout } = useAuth();
  const [dark, setDark] = useState(() => localStorage.getItem("theme") === "dark");
  const [open, setOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const editableNav = user?.role === "viewer" ? nav.filter((item) => ["dashboard", "insights", "reports"].includes(item.id)) : nav;
  const items = ["admin", "super_admin"].includes(user?.role)
    ? [...editableNav, { id: "integrations", label: "Integrations", icon: PlugZap }, { id: "settings", label: "Settings", icon: Settings }, { id: "admin", label: "Admin", icon: Shield }]
    : [...editableNav, { id: "settings", label: "Settings", icon: Settings }];
  const unread = notifications.filter((item) => !item.is_read).length;

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  const read = async (id) => {
    await api.post(`/notifications/${id}/read`);
    refreshNotifications();
  };

  const search = async (event) => {
    event.preventDefault();
    if (!query.trim()) return;
    const { data } = await api.get(`/search?q=${encodeURIComponent(query.trim())}`);
    setResults(data);
  };

  return (
    <div className="min-h-screen bg-cloud text-ink transition dark:bg-slate-950 dark:text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-white/60 bg-white/80 px-5 py-6 shadow-panel backdrop-blur-2xl dark:border-white/10 dark:bg-slate-900/75 lg:block">
        <div className="flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-lg bg-ocean text-white shadow-lg"><Database size={24} /></div>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-mint">Enterprise AI</p>
            <h1 className="text-lg font-black">Demand Forecasting</h1>
          </div>
        </div>
        <nav className="mt-10 space-y-2">
          {items.map((item) => {
            const Icon = item.icon;
            const active = activePage === item.id;
            return (
              <button key={item.id} onClick={() => setActivePage(item.id)} className={`nav-button ${active ? "nav-active" : ""}`}>
                <Icon size={19} /><span>{item.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="absolute bottom-5 left-5 right-5 rounded-lg border border-white/70 bg-white/60 p-4 text-sm shadow-sm dark:border-white/10 dark:bg-white/5">
          <p className="font-bold">Developed by Yogeshwaran K</p>
          <p className="mt-1 text-slate-500 dark:text-slate-400">Production-ready AI analytics workspace</p>
        </div>
      </aside>
      <main className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-white/70 bg-white/75 px-4 py-4 backdrop-blur-2xl dark:border-white/10 dark:bg-slate-950/80 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Welcome back, {user?.role}</p>
              <h2 className="text-2xl font-black">{user?.name}</h2>
            </div>
            <div className="flex items-center gap-2 overflow-x-auto">
              <div className="flex gap-1 lg:hidden">
                {items.map((item) => {
                  const Icon = item.icon;
                  return <button key={item.id} onClick={() => setActivePage(item.id)} className={`icon-button ${activePage === item.id ? "bg-ocean text-white" : ""}`} title={item.label}><Icon size={18} /></button>;
                })}
              </div>
              <button onClick={() => setDark(!dark)} className="icon-button" title="Toggle theme">{dark ? <Sun size={18} /> : <Moon size={18} />}</button>
              <div className="relative">
                <button onClick={() => setSearchOpen(!searchOpen)} className="icon-button" title="Global search"><Search size={18} /></button>
                {searchOpen && (
                  <form onSubmit={search} className="absolute right-0 mt-2 w-[23rem] rounded-lg border border-white/70 bg-white/95 p-3 shadow-panel dark:border-white/10 dark:bg-slate-900/95">
                    <div className="flex gap-2"><input className="input min-w-0 flex-1" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search datasets, models, users" /><button className="secondary-button" type="submit">Search</button></div>
                    {results && <div className="mt-3 max-h-72 space-y-3 overflow-auto text-sm">
                      <SearchGroup title="Datasets" rows={results.datasets.map((row) => row.name)} />
                      <SearchGroup title="Forecasts" rows={results.forecasts.map((row) => `${row.dataset} - ${row.model_name}`)} />
                      <SearchGroup title="Users" rows={results.users.map((row) => `${row.name} - ${row.role}`)} />
                    </div>}
                  </form>
                )}
              </div>
              <div className="relative">
                <button onClick={() => setOpen(!open)} className="icon-button" title="Notifications">
                  <Bell size={18} />{unread > 0 && <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-rose-500 px-1 text-xs font-bold text-white">{unread}</span>}
                </button>
                {open && (
                  <div className="absolute right-0 mt-2 w-[22rem] rounded-lg border border-white/70 bg-white/95 p-3 shadow-panel backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/95">
                    <div className="mb-3 flex items-center justify-between"><h3 className="font-black">Notifications</h3><span className="text-xs text-slate-500">{unread} unread</span></div>
                    <div className="max-h-80 space-y-2 overflow-auto">
                      {notifications.length === 0 && <EmptyState title="No notifications" />}
                      {notifications.map((item) => (
                        <button key={item.id} onClick={() => read(item.id)} className={`w-full rounded-lg border p-3 text-left text-sm transition hover:-translate-y-0.5 ${item.is_read ? "border-slate-200/70 bg-white/50 dark:border-white/10 dark:bg-white/5" : "border-mint/40 bg-mint/10"}`}>
                          <p className="font-bold">{item.title}</p>
                          <p className="mt-1 text-slate-600 dark:text-slate-300">{item.message}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <button onClick={logout} className="icon-button" title="Logout"><LogOut size={18} /></button>
            </div>
          </div>
        </header>
        <section className="px-4 py-6 lg:px-8">{children}</section>
      </main>
    </div>
  );
}

function EmptyState({ title }) {
  return <p className="rounded-lg border border-dashed border-slate-300 p-5 text-center text-sm text-slate-500 dark:border-white/10">{title}</p>;
}

function SearchGroup({ title, rows }) {
  if (!rows.length) return null;
  return <div><p className="mb-1 text-xs font-black uppercase text-slate-400">{title}</p>{rows.map((row) => <p key={row} className="rounded-md px-2 py-1.5 hover:bg-slate-100 dark:hover:bg-white/10">{row}</p>)}</div>;
}




