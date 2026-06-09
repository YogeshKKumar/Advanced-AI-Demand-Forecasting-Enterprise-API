import React, { useEffect, useState } from "react";
import { BriefcaseBusiness, Database, Plus } from "lucide-react";
import api from "../api/client";
import DatasetPicker from "../components/DatasetPicker";
import DataTable from "../components/DataTable";

export default function WorkspacesPage({ datasets, selectedDatasetId, setSelectedDatasetId, refresh }) {
  const [projects, setProjects] = useState([]);
  const [activity, setActivity] = useState([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [form, setForm] = useState({ name: "Executive demand workspace", description: "Forecasts, datasets, reports, and decisions for leadership review." });

  const load = async () => {
    const { data } = await api.get("/projects");
    setProjects(data);
    if (!selectedProject && data.length) setSelectedProject(String(data[0].id));
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!selectedProject) return;
    api.get(`/projects/${selectedProject}/activity`).then(({ data }) => setActivity(data));
  }, [selectedProject]);

  const createProject = async (event) => {
    event.preventDefault();
    await api.post("/projects", form);
    await load();
  };
  const attachDataset = async () => {
    if (!selectedProject || !selectedDatasetId) return;
    await api.post(`/projects/${selectedProject}/datasets`, { dataset_id: Number(selectedDatasetId) });
    await load();
    await refresh?.();
  };

  return (
    <div className="space-y-6">
      <div><p className="page-eyebrow">Forecast workspace management</p><h2 className="page-title">Forecast projects</h2></div>
      <form onSubmit={createProject} className="panel grid gap-3 lg:grid-cols-[1fr_1.5fr_auto]">
        <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <button className="secondary-button h-12 inline-flex items-center gap-2"><Plus size={16}/>Create</button>
      </form>
      <section className="panel">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h3 className="text-lg font-black">Workspace inventory</h3><select className="input h-10" value={selectedProject} onChange={(e) => setSelectedProject(e.target.value)}>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></div>
        <DataTable columns={[{ key: "name", label: "Project" }, { key: "dataset_count", label: "Datasets" }, { key: "forecast_count", label: "Forecasts" }, { key: "status", label: "Status" }]} rows={projects} />
      </section>
      <section className="panel">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h3 className="flex items-center gap-2 text-lg font-black"><Database size={19}/>Attach dataset</h3><DatasetPicker datasets={datasets} selectedDatasetId={selectedDatasetId} setSelectedDatasetId={setSelectedDatasetId}/><button className="secondary-button" onClick={attachDataset}>Attach</button></div>
        <div className="grid gap-3 md:grid-cols-3">{activity.slice(0, 9).map((item) => <div className="activity-row" key={item.id}><BriefcaseBusiness size={17}/><div><b>{item.action}</b><p className="text-sm text-slate-500">{new Date(item.created_at).toLocaleString()}</p></div></div>)}</div>
      </section>
    </div>
  );
}
