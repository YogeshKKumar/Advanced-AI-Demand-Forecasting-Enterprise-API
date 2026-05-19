import React, { useState } from "react";
import { CheckCircle2, UploadCloud } from "lucide-react";
import api from "../api/client";

export default function UploadPage({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setStatus(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const { data } = await api.post("/datasets/upload", form, { headers: { "Content-Type": "multipart/form-data" } });
      setStatus(data.validation);
      onUploaded?.(data.dataset.id);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div><p className="page-eyebrow">Data operations</p><h2 className="page-title">Upload demand dataset</h2></div>
      <div className="panel">
        <label className="grid cursor-pointer place-items-center rounded-lg border-2 border-dashed border-slate-300 px-6 py-16 text-center transition hover:border-mint hover:bg-mint/5 dark:border-white/10">
          <UploadCloud size={44} className="text-ocean" />
          <p className="mt-4 text-xl font-black">{file ? file.name : "Drop or select CSV / Excel dataset"}</p>
          <p className="mt-2 text-slate-500">Required columns: date, product, quantity, sales. Optional: category, region.</p>
          <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={(event) => setFile(event.target.files?.[0])} />
        </label>
        <button onClick={upload} disabled={!file || busy} className="mt-5 h-12 rounded-lg bg-ocean px-6 font-black text-white shadow-lg transition hover:-translate-y-0.5 disabled:opacity-50">{busy ? "Validating data..." : "Upload Dataset"}</button>
      </div>
      {status && <div className="panel flex items-start gap-3"><CheckCircle2 className="text-mint" /><div><h3 className="font-black">Dataset is ready</h3><p className="mt-1 text-slate-500">{status.clean_rows} clean rows, {status.products} products, {status.categories} categories, {status.regions} regions.</p></div></div>}
    </div>
  );
}
