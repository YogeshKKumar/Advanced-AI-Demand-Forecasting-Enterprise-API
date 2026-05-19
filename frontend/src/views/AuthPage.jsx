import React, { useState } from "react";
import { BrainCircuit, Lock, Mail, User } from "lucide-react";
import { useAuth } from "../state/AuthContext";

export default function AuthPage() {
  const { authenticate, busy } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "Yogeshwaran K", email: "admin@forecast.ai", password: "Forecast@123" });
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await authenticate(mode, form);
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.detail || "Authentication failed");
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,#dff7f3,transparent_34%),linear-gradient(135deg,#f8fafc,#e2eef5)] px-4 py-8 dark:bg-slate-950">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1.08fr_0.92fr]">
        <section>
          <div className="mb-8 flex items-center gap-3">
            <div className="grid h-14 w-14 place-items-center rounded-lg bg-ocean p-3 text-white shadow-panel"><BrainCircuit size={30} /></div>
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.22em] text-ocean">Enterprise Platform</p>
              <h1 className="text-4xl font-black leading-tight text-ink md:text-6xl">Advanced AI Demand Forecasting</h1>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {["Linear Regression", "Random Forest", "XGBoost + Prophet"].map((item) => <div key={item} className="rounded-lg border border-white/70 bg-white/60 p-5 shadow-sm backdrop-blur"><p className="font-black text-ink">{item}</p><p className="mt-2 text-sm text-slate-600">Production model analytics</p></div>)}
          </div>
        </section>
        <form onSubmit={submit} className="rounded-lg border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur-2xl dark:border-white/10 dark:bg-slate-900/80">
          <div className="mb-6 flex rounded-lg bg-slate-100 p-1 dark:bg-white/10">
            {["login", "register"].map((item) => <button key={item} type="button" onClick={() => setMode(item)} className={`h-11 flex-1 rounded-md text-sm font-black capitalize transition ${mode === item ? "bg-white text-ocean shadow-sm dark:bg-slate-800" : "text-slate-500"}`}>{item}</button>)}
          </div>
          {mode === "register" && <Field icon={User} label="Name" value={form.name} onChange={(value) => setForm({ ...form, name: value })} />}
          <Field icon={Mail} label="Email" value={form.email} onChange={(value) => setForm({ ...form, email: value })} />
          <Field icon={Lock} label="Password" type="password" value={form.password} onChange={(value) => setForm({ ...form, password: value })} />
          {error && <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm font-semibold text-rose-700">{error}</p>}
          <button className="h-12 w-full rounded-lg bg-ocean font-black text-white shadow-lg transition hover:-translate-y-0.5 hover:bg-cyan-800 disabled:opacity-60" disabled={busy}>{busy ? "Securing workspace..." : mode === "login" ? "Login" : "Create Account"}</button>
        </form>
      </div>
    </div>
  );
}

function Field({ icon: Icon, label, value, onChange, type = "text" }) {
  return (
    <label className="mb-4 block">
      <span className="mb-2 block text-sm font-bold text-slate-600 dark:text-slate-300">{label}</span>
      <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 dark:border-white/10 dark:bg-white/5">
        <Icon size={18} className="text-slate-400" />
        <input className="h-12 flex-1 bg-transparent text-sm outline-none" type={type} value={value} onChange={(event) => onChange(event.target.value)} required />
      </div>
    </label>
  );
}
