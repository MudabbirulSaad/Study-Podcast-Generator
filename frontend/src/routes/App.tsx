import { AudioLines, Download, FolderOpen, Play, Settings, Timer, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { apiClient, type ApiClient } from "../api/client";
import type { Job, Project, QueueSummary, RuntimeSettings, RuntimeStatus, ScriptResponse } from "../types/api";

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
  const audioUrl = project ? client.audioStreamUrl(project.id) : "";
  const downloadUrl = project ? client.finalAudioUrl(project.id) : "";

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

  async function uploadScript(file: File | null) {
    if (!project) {
      setMessage("Create a project first.");
      return;
    }
    if (!file) {
      return;
    }
    setScript(await client.uploadScript(project.id, file));
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
        <label className="file-button">
          Upload TXT
          <input
            aria-label="Upload TXT"
            accept=".txt,text/plain"
            type="file"
            onChange={(event) => void uploadScript(event.target.files?.[0] ?? null)}
          />
        </label>
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
            <div className="audio-actions">
              <audio controls src={audioUrl}>
                <track kind="captions" />
              </audio>
              <a className="action-link" href={downloadUrl} download>
                <Download aria-hidden="true" />
                Download WAV
              </a>
              <a className="action-link" href={audioUrl}>
                <Play aria-hidden="true" />
                Open Stream
              </a>
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

const activeJobStatuses = ["queued", "running", "cancel_requested"];

function JobsRoute({ client }: { client: ApiClient }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [queue, setQueue] = useState<QueueSummary | null>(null);
  const [message, setMessage] = useState("");

  async function refreshJobs() {
    const [jobsResult, queueResult] = await Promise.allSettled([client.listJobs(), client.getQueue()]);
    if (jobsResult.status === "fulfilled") {
      setJobs(jobsResult.value);
    } else {
      setMessage("Job history unavailable.");
    }
    if (queueResult.status === "fulfilled") {
      setQueue(queueResult.value);
    } else {
      setMessage("Queue summary unavailable.");
    }
  }

  useEffect(() => {
    void refreshJobs();
  }, []);

  async function cancelJob(jobId: string) {
    setMessage("");
    await client.cancelJob(jobId);
    await refreshJobs();
  }

  return (
    <section className="workspace-panel flow-grid">
      <div>
        <p className="eyebrow">Queue</p>
        <h1>Generation Jobs</h1>
        <p>Queued, running, completed, cancelled, failed, and interrupted jobs.</p>
      </div>

      {queue && (
        <section className="data-section" aria-label="Queue summary">
          <h2>Queue Summary</h2>
          <p>
            {queue.pending_count} pending / {queue.running_count} running / {queue.completed_count} completed
          </p>
          <p>Max active jobs: {queue.max_active_jobs_total}</p>
        </section>
      )}

      {message && <p className="message">{message}</p>}

      <section className="job-list" aria-label="Job history">
        {jobs.length === 0 && <p>No generation jobs yet.</p>}
        {jobs.map((job) => {
          const queuePosition = queue?.queue_positions[job.id] ?? null;
          const canCancel = activeJobStatuses.includes(job.status);
          return (
            <article className="job-card" key={job.id}>
              <div className="job-head">
                <div>
                  <h2>{job.id}</h2>
                  <p>{job.status} / {job.phase} / {job.progress_percent}%</p>
                  <p>Project {job.project_id}</p>
                </div>
                {canCancel && (
                  <button
                    className="icon-button"
                    onClick={() => {
                      void cancelJob(job.id);
                    }}
                    aria-label={`Cancel job ${job.id}`}
                  >
                    <XCircle aria-hidden="true" />
                  </button>
                )}
              </div>
              <div className="meter" aria-label={`Progress for job ${job.id}`}>
                <span style={{ width: `${job.progress_percent}%` }} />
              </div>
              <p>
                {job.completed_chunks} / {job.total_chunks} chunks
                {queuePosition ? ` / queue position ${queuePosition}` : ""}
              </p>
              {job.current_chunk_preview && <p>{job.current_chunk_preview}</p>}
              {job.message && <p className="message">{job.message}</p>}
              {job.failure_reason && job.failure_reason !== job.message && (
                <p className="message">{job.failure_reason}</p>
              )}
            </article>
          );
        })}
      </section>
    </section>
  );
}

function SettingsRoute({ client }: { client: ApiClient }) {
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [values, setValues] = useState<RuntimeSettings["values"]>({});
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    void client.getSettings().then((loaded) => {
      setSettings(loaded);
      setValues(loaded.values);
    });
  }, [client]);

  useEffect(() => {
    if (!runtime || !["reload_pending", "reloading"].includes(runtime.status)) {
      return;
    }
    const timer = window.setInterval(async () => {
      const next = await client.getRuntimeStatus();
      setRuntime(next);
      if (["ready", "failed"].includes(next.status)) {
        window.clearInterval(timer);
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [client, runtime]);

  function updateValue(key: string, value: string | boolean) {
    const current = values[key];
    const nextValue = typeof current === "number" ? Number(value) : value;
    setValues((existing) => ({ ...existing, [key]: nextValue }));
  }

  async function saveSettings() {
    setMessage("");
    const saved = await client.saveSettings(values);
    setSettings(saved);
    setValues(saved.values);
    setRuntime({
      status: saved.runtime_status,
      active_engine: String(saved.values.active_tts_engine),
      reload_required: saved.reload_required,
      last_reload_error: saved.last_reload_error,
    });
  }

  async function reloadBackendEngine() {
    setMessage("");
    const status = await client.reloadSettings();
    setRuntime(status);
    const refreshed = await client.getSettings();
    setSettings(refreshed);
    setValues(refreshed.values);
  }

  const runtimeStatus = runtime?.status ?? settings?.runtime_status ?? "idle";
  const activeEngine = runtime?.active_engine ?? String(values.active_tts_engine ?? "");
  const reloadRequired = runtime?.reload_required ?? settings?.reload_required ?? false;
  const reloadError = runtime?.last_reload_error ?? settings?.last_reload_error;

  return (
    <section className="workspace-panel flow-grid">
      <p className="eyebrow">Settings</p>
      <h1>TTS Settings</h1>
      <p>Chatterbox is the local TTS engine. The development test engine appears only when enabled.</p>
      {settings && (
        <>
          <section className="data-section" aria-label="Runtime status">
            <h2>Runtime</h2>
            {reloadRequired && <p className="message">Reload required</p>}
            {runtimeStatus === "ready" && <p className="status-line">Runtime ready: {activeEngine}</p>}
            {runtimeStatus !== "ready" && <p className="status-line">Runtime status: {runtimeStatus}</p>}
            {reloadError && <p className="message">{reloadError}</p>}
          </section>

          <section className="data-section settings-grid" aria-label="Editable settings">
            <label>
              TTS engine
              <select
                aria-label="TTS engine"
                value={String(values.active_tts_engine ?? "")}
                onChange={(event) => updateValue("active_tts_engine", event.target.value)}
              >
                {settings.available_engines.map((engine) => (
                  <option key={engine} value={engine}>
                    {engine}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Chatterbox device
              <select
                aria-label="Chatterbox device"
                value={String(values.chatterbox_device ?? "auto")}
                onChange={(event) => updateValue("chatterbox_device", event.target.value)}
              >
                <option value="auto">auto</option>
                <option value="cpu">cpu</option>
                <option value="cuda">cuda</option>
              </select>
            </label>
            {[
              ["max_script_size_bytes", "Max script size bytes"],
              ["max_chunk_chars", "Max chunk chars"],
              ["max_chunks", "Max chunks"],
              ["chatterbox_max_concurrent_jobs", "Chatterbox max concurrent jobs"],
              ["audio_merge_max_concurrent_jobs", "Audio merge max concurrent jobs"],
              ["max_active_jobs_total", "Max active jobs total"],
            ].map(([key, label]) => (
              <label key={key}>
                {label}
                <input
                  aria-label={label}
                  type="number"
                  value={Number(values[key] ?? 0)}
                  onChange={(event) => updateValue(key, event.target.value)}
                />
              </label>
            ))}
            <label>
              Storage root
              <input
                aria-label="Storage root"
                value={String(values.storage_root ?? "")}
                onChange={(event) => updateValue("storage_root", event.target.value)}
              />
            </label>
            <label>
              Frontend origin
              <input
                aria-label="Frontend origin"
                value={String(values.frontend_origin ?? "")}
                onChange={(event) => updateValue("frontend_origin", event.target.value)}
              />
            </label>
            <label className="checkbox-line">
              <input
                aria-label="Serve frontend"
                type="checkbox"
                checked={Boolean(values.serve_frontend)}
                onChange={(event) => updateValue("serve_frontend", event.target.checked)}
              />
              Serve frontend from FastAPI
            </label>
          </section>

          <div className="tool-row">
            <button onClick={saveSettings}>Save settings</button>
            {reloadRequired && <button onClick={reloadBackendEngine}>Reload backend engine</button>}
          </div>
          {message && <p className="message">{message}</p>}
        </>
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
          <Route path="/jobs" element={<JobsRoute client={client} />} />
          <Route path="/settings" element={<SettingsRoute client={client} />} />
        </Routes>
      </main>
    </div>
  );
}
