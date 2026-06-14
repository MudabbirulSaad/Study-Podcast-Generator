import { AudioLines, Download, FolderOpen, Play, Settings, Timer, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { apiClient, type ApiClient } from "../api/client";
import type { Job, Project, QueueSummary, ScriptResponse, TtsSettings } from "../types/api";

type AppProps = {
  client?: ApiClient;
};

function ProjectsRoute({ client }: { client: ApiClient }) {
  const [title, setTitle] = useState("Biology 101");
  const [project, setProject] = useState<Project | null>(null);
  const [script, setScript] = useState<ScriptResponse | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [queue, setQueue] = useState<QueueSummary | null>(null);
  const [scriptText, setScriptText] = useState("[S1] Cells divide. [Narrator] Tissues grow.");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!job || ["completed", "failed", "cancelled", "interrupted"].includes(job.status)) {
      return;
    }
    const timer = window.setInterval(async () => {
      const [updatedJob, updatedQueue] = await Promise.all([client.getJob(job.id), client.getQueue()]);
      setJob(updatedJob);
      setQueue(updatedQueue);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [client, job]);

  const queuePosition = useMemo(() => {
    if (!job || !queue) {
      return null;
    }
    return queue.queue_positions[job.id] ?? null;
  }, [job, queue]);

  async function createProject() {
    setMessage("");
    setProject(await client.createProject(title));
  }

  async function saveScript() {
    if (!project) {
      setMessage("Create a project first.");
      return;
    }
    setScript(await client.saveScript(project.id, scriptText));
  }

  async function startJob() {
    if (!project) {
      setMessage("Create a project first.");
      return;
    }
    const started = await client.startJob(project.id);
    setJob(started);
    setQueue(await client.getQueue());
  }

  async function cancelJob() {
    if (!job) {
      return;
    }
    setJob(await client.cancelJob(job.id));
    setQueue(await client.getQueue());
  }

  return (
    <section className="workspace-panel flow-grid">
      <div>
        <p className="eyebrow">Projects</p>
        <h1>Study Podcast Generator</h1>
      </div>
      <div className="tool-row">
        <input value={title} onChange={(event) => setTitle(event.target.value)} aria-label="Project title" />
        <button onClick={createProject}>Create Project</button>
      </div>
      {project && <p className="status-line">Active project: {project.title}</p>}

      <label className="editor-label" htmlFor="script">
        Script
      </label>
      <textarea id="script" value={scriptText} onChange={(event) => setScriptText(event.target.value)} />
      <div className="tool-row">
        <button onClick={saveScript}>Save Script</button>
        <button onClick={startJob}>Start Generation</button>
      </div>
      {message && <p className="message">{message}</p>}

      {script && (
        <section className="data-section" aria-label="Chunk preview">
          <h2>Chunks And Speakers</h2>
          <p>{script.speakers.join(", ") || "Narrator"}</p>
          <ol className="chunk-list">
            {script.chunks.map((chunk) => (
              <li key={chunk.index}>
                <strong>{chunk.speaker}</strong>
                <span>{chunk.text}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {job && (
        <section className="data-section" aria-label="Job progress">
          <div className="job-head">
            <h2>Job Progress</h2>
            {["queued", "running", "cancel_requested"].includes(job.status) && (
              <button className="icon-button" onClick={cancelJob} aria-label="Cancel job">
                <XCircle aria-hidden="true" />
              </button>
            )}
          </div>
          <div className="meter" aria-label="Progress percent">
            <span style={{ width: `${job.progress_percent}%` }} />
          </div>
          <p>
            {job.status} / {job.phase} / {job.progress_percent}%
          </p>
          <p>
            {job.completed_chunks} / {job.total_chunks} chunks
            {queuePosition ? ` / queue position ${queuePosition}` : ""}
          </p>
          {job.message && <p className="message">{job.message}</p>}
          {["completed"].includes(job.status) && (
            <div className="tool-row">
              <button>
                <Play aria-hidden="true" />
                Play
              </button>
              <button>
                <Download aria-hidden="true" />
                Download WAV
              </button>
            </div>
          )}
        </section>
      )}
    </section>
  );
}

function ProjectDetailRoute() {
  return (
    <section className="workspace-panel">
      <p className="eyebrow">Project</p>
      <h1>Project Workspace</h1>
      <p>Script editing, chunk preview, job progress, and final audio live here.</p>
    </section>
  );
}

function JobsRoute() {
  return (
    <section className="workspace-panel">
      <p className="eyebrow">Queue</p>
      <h1>Generation Jobs</h1>
      <p>Queued, running, completed, cancelled, failed, and interrupted jobs.</p>
    </section>
  );
}

function SettingsRoute({ client }: { client: ApiClient }) {
  const [settings, setSettings] = useState<TtsSettings | null>(null);

  useEffect(() => {
    void client.getTtsSettings().then(setSettings);
  }, [client]);

  return (
    <section className="workspace-panel">
      <p className="eyebrow">Settings</p>
      <h1>TTS Settings</h1>
      <p>Fake TTS is the default. Chatterbox can be enabled after local setup.</p>
      {settings && (
        <p className="status-line">
          Active: {settings.active_engine}. Available: {settings.available_engines.join(", ")}.
        </p>
      )}
    </section>
  );
}

export function App({ client = apiClient }: AppProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <AudioLines aria-hidden="true" />
          <span>StudyCast</span>
        </div>
        <nav aria-label="Primary">
          <NavLink to="/" end>
            <FolderOpen aria-hidden="true" />
            Projects
          </NavLink>
          <NavLink to="/jobs">
            <Timer aria-hidden="true" />
            Jobs
          </NavLink>
          <NavLink to="/settings">
            <Settings aria-hidden="true" />
            Settings
          </NavLink>
        </nav>
      </aside>
      <main className="workspace">
        <Routes>
          <Route path="/" element={<ProjectsRoute client={client} />} />
          <Route path="/projects/:projectId" element={<ProjectDetailRoute />} />
          <Route path="/jobs" element={<JobsRoute />} />
          <Route path="/settings" element={<SettingsRoute client={client} />} />
        </Routes>
      </main>
    </div>
  );
}
