import React, { useEffect, useState } from "react";
import { MessageSquareText, Share2 } from "lucide-react";
import api from "../api/client";
import DataTable from "../components/DataTable";

export default function CollaborationPage() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [comments, setComments] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [body, setBody] = useState("");
  const [email, setEmail] = useState("");

  const loadProjects = async () => {
    const { data } = await api.get("/projects");
    setProjects(data);
    if (!projectId && data[0]) setProjectId(String(data[0].id));
  };
  const load = async () => {
    if (!projectId) return;
    const [c, t] = await Promise.all([api.get(`/collaboration/projects/${projectId}/comments`), api.get(`/collaboration/projects/${projectId}/timeline`)]);
    setComments(c.data);
    setTimeline(t.data);
  };
  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { load(); }, [projectId]);

  const comment = async (event) => {
    event.preventDefault();
    if (!body.trim()) return;
    await api.post(`/collaboration/projects/${projectId}/comments`, { body });
    setBody("");
    await load();
  };
  const share = async (event) => {
    event.preventDefault();
    if (!email.trim()) return;
    await api.post(`/collaboration/projects/${projectId}/shares`, { recipient_email: email, access_level: "view" });
    setEmail("");
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="page-eyebrow">Forecast collaboration</p><h2 className="page-title">Comments, sharing and activity</h2></div><select className="input" value={projectId} onChange={(e) => setProjectId(e.target.value)}>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></div>
      <div className="grid gap-5 xl:grid-cols-2">
        <form onSubmit={comment} className="panel space-y-3"><h3 className="flex items-center gap-2 text-lg font-black"><MessageSquareText size={19}/>Add forecast comment</h3><textarea className="input h-28 w-full py-3" value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write project or forecast note"/><button className="secondary-button">Post comment</button></form>
        <form onSubmit={share} className="panel space-y-3"><h3 className="flex items-center gap-2 text-lg font-black"><Share2 size={19}/>Share report</h3><input className="input w-full" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="recipient@company.com"/><button className="secondary-button">Share</button></form>
      </div>
      <section className="panel"><h3 className="mb-4 text-lg font-black">Comments</h3><DataTable columns={[{ key: "body", label: "Comment" }, { key: "created_at", label: "Created", render: (row) => new Date(row.created_at).toLocaleString() }]} rows={comments}/></section>
      <section className="panel"><h3 className="mb-4 text-lg font-black">Activity timeline</h3><DataTable columns={[{ key: "action", label: "Action" }, { key: "created_at", label: "Created", render: (row) => new Date(row.created_at).toLocaleString() }]} rows={timeline}/></section>
    </div>
  );
}
