import React, { useState } from "react";
import { CheckCircle2, Upload } from "lucide-react";
import gateway from "../services/gateway";

export default function ImportDesk({ afterImport }) {
  const [file, setFile] = useState(null);
  const [profile, setProfile] = useState(null);
  const [busy, setBusy] = useState(false);

  const send = async () => {
    if (!file) return;
    setBusy(true);
    const body = new FormData();
    body.append("file", file);
    try {
      const { data } = await gateway.post("/workbooks/import", body, { headers: { "Content-Type": "multipart/form-data" } });
      setProfile(data.profile);
      afterImport?.(data.workbook.id);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div><p className="section-label">Workbook intake</p><h2 className="section-title">Import demand history</h2></div>
      <section className="surface">
        <label className="grid cursor-pointer place-items-center rounded-3xl border-2 border-dashed border-green-200 bg-limewash px-6 py-16 text-center transition hover:border-leaf">
          <Upload size={42} className="text-leaf" />
          <p className="mt-4 text-xl font-black">{file ? file.name : "Select CSV or Excel workbook"}</p>
          <p className="mt-2 text-slate-500">Required: date, product, quantity, sales. Optional: category, region.</p>
          <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={(event) => setFile(event.target.files?.[0])} />
        </label>
        <button className="primary-action mt-5" onClick={send} disabled={!file || busy}>{busy ? "Profiling workbook..." : "Import Workbook"}</button>
      </section>
      {profile && <section className="surface flex gap-3"><CheckCircle2 className="text-leaf" /><div><h3 className="font-black">Workbook accepted</h3><p className="text-slate-500">{profile.accepted_rows} rows, {profile.items} items, {profile.segments} segments, {profile.markets} markets.</p></div></section>}
    </div>
  );
}
