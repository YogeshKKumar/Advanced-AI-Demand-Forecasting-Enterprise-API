import React, { useState } from "react";
import { Leaf, Lock, Mail, UserRound } from "lucide-react";
import { useIdentity } from "../state/IdentityProvider";

export default function EntryScreen() {
  const { enter, working } = useIdentity();
  const [mode, setMode] = useState("signin");
  const [form, setForm] = useState({ full_name: "Priya", email: "priya@forecast.ai", password: "Priya@123" });
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await enter(mode, form);
    } catch (err) {
      setError(err.response?.data?.detail || "Access failed");
    }
  };

  return (
    <main className="min-h-screen bg-limewash px-5 py-8">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1fr_0.85fr]">
        <section>
          <div className="mb-8 inline-flex items-center gap-3 rounded-full border border-green-200 bg-white px-4 py-2 text-sm font-black text-leaf shadow-sm">
            <Leaf size={18} /> Corporate Demand Enhancement
          </div>
          <h1 className="max-w-3xl text-5xl font-black leading-tight text-graphite">Advanced AI Demand Forecasting Enhancement</h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">A green corporate workspace for clean demand planning, scenario analysis, and board-ready forecasting reports.</p>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {["Workbook Intake", "Scenario Quality", "Export Studio"].map((item) => <div className="rounded-2xl border border-green-100 bg-white p-5 shadow-corporate" key={item}><p className="font-black text-graphite">{item}</p><p className="mt-2 text-sm text-slate-500">Built for repeatable planning.</p></div>)}
          </div>
        </section>
        <form onSubmit={submit} className="rounded-3xl border border-green-100 bg-white p-7 shadow-corporate">
          <div className="mb-6 grid grid-cols-2 rounded-2xl bg-limewash p-1">
            {["signin", "signup"].map((item) => <button key={item} type="button" onClick={() => setMode(item)} className={`h-11 rounded-xl text-sm font-black capitalize ${mode === item ? "bg-leaf text-white shadow" : "text-slate-500"}`}>{item}</button>)}
          </div>
          {mode === "signup" && <Field icon={UserRound} label="Full name" value={form.full_name} onChange={(value) => setForm({ ...form, full_name: value })} />}
          <Field icon={Mail} label="Email" value={form.email} onChange={(value) => setForm({ ...form, email: value })} />
          <Field icon={Lock} label="Password" type="password" value={form.password} onChange={(value) => setForm({ ...form, password: value })} />
          {error && <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm font-bold text-red-700">{error}</p>}
          <button className="h-12 w-full rounded-2xl bg-leaf font-black text-white shadow-lg transition hover:bg-green-700 disabled:opacity-60" disabled={working}>{working ? "Opening workspace..." : "Continue"}</button>
        </form>
      </div>
    </main>
  );
}

function Field({ icon: Icon, label, value, onChange, type = "text" }) {
  return (
    <label className="mb-4 block">
      <span className="mb-2 block text-sm font-black text-slate-600">{label}</span>
      <div className="flex items-center gap-2 rounded-2xl border border-green-100 bg-white px-3">
        <Icon size={18} className="text-leaf" />
        <input className="h-12 flex-1 outline-none" type={type} value={value} onChange={(event) => onChange(event.target.value)} required />
      </div>
    </label>
  );
}
