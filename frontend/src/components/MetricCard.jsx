import React from "react";

const tones = {
  ocean: "bg-ocean",
  mint: "bg-mint",
  amber: "bg-amber"
};

export default function MetricCard({ icon: Icon, label, value, trend, tone = "ocean" }) {
  return (
    <div className="metric-card">
      <div className={`grid h-11 w-11 place-items-center rounded-lg ${tones[tone] || tones.ocean} text-white shadow-lg`}>
        <Icon size={21} />
      </div>
      <div>
        <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
        <h3 className="mt-1 text-2xl font-black">{value}</h3>
        <p className="mt-1 text-xs font-semibold text-mint">{trend}</p>
      </div>
    </div>
  );
}


