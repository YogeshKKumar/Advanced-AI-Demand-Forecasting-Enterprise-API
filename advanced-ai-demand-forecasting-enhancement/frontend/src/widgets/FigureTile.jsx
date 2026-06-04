import React from "react";

export default function FigureTile({ icon: Icon, label, value }) {
  return (
    <div className="figure-tile">
      <div className="grid h-11 w-11 place-items-center rounded-2xl bg-leaf text-white"><Icon size={21}/></div>
      <div><p className="text-sm font-bold text-slate-500">{label}</p><h3 className="mt-1 text-2xl font-black">{value}</h3></div>
    </div>
  );
}
