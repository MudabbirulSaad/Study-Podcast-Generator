import {
  AudioLines,
  CheckCircle2,
  CircleAlert,
  Download,
  FolderOpen,
  Moon,
  Plus,
  Search,
  Settings,
  SlidersHorizontal,
  Sun,
  Timer,
  Upload,
  XCircle,
} from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { apiClient, type ApiClient } from "../api/client";
import { AudioPlayer } from "../components/AudioPlayer";
import type {
  Job,
  Project,
  QueueSummary,
  RuntimeSettings,
  RuntimeStatus,
  ScriptResponse,
  VoiceProfile,
} from "../types/api";

type AppProps = {
  client?: ApiClient;
};

type ThemePreference = "system" | "light" | "dark";

const activeJobStatuses = ["queued", "running", "cancel_requested"];
const terminalJobStatuses = ["completed", "failed", "cancelled", "interrupted"];

function useThemePreference() {
  const [theme, setTheme] = useState<ThemePreference>(() => {
    const stored = window.localStorage.getItem("studycast-theme");
    return stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
  });

  useEffect(() => {
    window.localStorage.setItem("studycast-theme", theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  return { theme, setTheme };
}

function shortId(id: string) {
  return id.length > 12 ? `${id.slice(0, 8)}...${id.slice(-4)}` : id;
}

function formatDate(value: string | null) {
  if (!value) {
    return "Not started";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function statusTone(status: string) {
  if (status === "completed" || status === "ready") {
    return "success";
  }
  if (status === "failed" || status === "interrupted" || status === "cancelled") {
    return "danger";
  }
  if (activeJobStatuses.includes(status) || status === "reload_pending" || status === "reloading") {
    return "warning";
  }
  return "neutral";
}

function Panel({
  children,
  className = "",
  label,
}: {
  children: ReactNode;
  className?: string;
  label?: string;
}) {
  return (
    <section className={`panel ${className}`} aria-label={label}>
      {children}
    </section>
  );
}

function StatusBadge({ value }: { value: string }) {
  return <span className={`status-badge ${statusTone(value)}`}>{value.replace("_", " ")}</span>;
}

function ProgressBar({ value, label }: { value: number; label: string }) {
  return (
    <div className="progress-track" aria-label={label}>
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

function SearchField({
  label,
  onChange,
  placeholder,
  value,
}: {
  label: string;
  onChange(value: string): void;
  placeholder: string;
  value: string;
}) {
  return (
    <label className="search-field">
      <Search aria-hidden="true" />
      <span className="sr-only">{label}</span>
      <input
        aria-label={label}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function SegmentedControl({
  label,
  onChange,
  options,
  value,
}: {
  label: string;
  onChange(value: string): void;
  options: { label: string; value: string }[];
  value: string;
}) {
  return (
    <div className="segmented-control" aria-label={label}>
      {options.map((option) => (
        <button
          className={value === option.value ? "is-selected" : ""}
          key={option.value}
          onClick={() => onChange(option.value)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Header({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children && <div className="header-actions">{children}</div>}
    </header>
  );
}

function ThemeToggle({
  setTheme,
  theme,
}: {
  setTheme(theme: ThemePreference): void;
  theme: ThemePreference;
}) {
  const nextTheme = theme === "system" ? "dark" : theme === "dark" ? "light" : "system";
  const label = theme === "system" ? "Theme: system" : `Theme: ${theme}`;
  return (
    <button
      className="ghost-button theme-button"
      type="button"
      aria-label={label}
      onClick={() => setTheme(nextTheme)}
      title="Toggle theme"
    >
      {theme === "dark" ? <Moon aria-hidden="true" /> : theme === "light" ? <Sun aria-hidden="true" /> : <SlidersHorizontal aria-hidden="true" />}
      <span>{theme}</span>
    </button>
  );
}

function AppShell({
  children,
  setTheme,
  theme,
}: {
  children: ReactNode;
  setTheme(theme: ThemePreference): void;
  theme: ThemePreference;
}) {
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
            <span>Projects</span>
          </NavLink>
          <NavLink to="/jobs">
            <Timer aria-hidden="true" />
            <span>Jobs</span>
          </NavLink>
          <NavLink to="/settings">
            <Settings aria-hidden="true" />
            <span>Settings</span>
          </NavLink>
        </nav>
        <ThemeToggle theme={theme} setTheme={setTheme} />
      </aside>
      <main className="workspace">{children}</main>
    </div>
  );
}

function ProjectsRoute({ client }: { client: ApiClient }) {
  const [title, setTitle] = useState("Biology 101");
  const [projectSearch, setProjectSearch] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [script, setScript] = useState<ScriptResponse | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [queue, setQueue] = useState<QueueSummary | null>(null);
  const [voices, setVoices] = useState<VoiceProfile[]>([]);
  const [voiceId, setVoiceId] = useState("default");
  const [voiceName, setVoiceName] = useState("My voice");
  const [ttsParams, setTtsParams] = useState({
    exaggeration: 0.5,
    cfg_weight: 0.5,
    temperature: 0.8,
    top_p: 1,
    min_p: 0.05,
    repetition_penalty: 1.2,
  });
  const [scriptText, setScriptText] = useState("[S1] Cells divide. [Narrator] Tissues grow.");
  const [message, setMessage] = useState("");
  const audioVersion = job?.status === "completed" ? job.id : undefined;
  const audioUrl = job?.status === "completed" ? client.jobAudioStreamUrl(job.id, audioVersion) : "";
  const downloadUrl = job?.status === "completed" ? client.jobFinalAudioUrl(job.id, audioVersion) : "";

  async function openProject(nextProject: Project) {
    setMessage("");
    setProject(nextProject);
    setJob(null);
    try {
      const loadedScript = await client.getScript(nextProject.id);
      setScript(loadedScript);
      setScriptText(loadedScript.text);
    } catch {
      setScript(null);
      setScriptText("");
    }
  }

  async function loadProjects(query = projectSearch) {
    const loaded = await client.listProjects(query ? { q: query } : undefined);
    setProjects(loaded);
    if (!project && loaded.length > 0) {
      await openProject(loaded[0]);
    }
  }

  useEffect(() => {
    void loadProjects("");
    void client.listVoices().then(setVoices);
  }, []);

  useEffect(() => {
    void loadProjects(projectSearch);
  }, [projectSearch]);

  useEffect(() => {
    if (!job || terminalJobStatuses.includes(job.status)) {
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
    const created = await client.createProject(title);
    setProjects([created, ...projects.filter((item) => item.id !== created.id)]);
    await openProject(created);
  }

  async function saveScript() {
    if (!project) {
      setMessage("Create a project first.");
      return;
    }
    const saved = await client.saveScript(project.id, scriptText);
    setScript(saved);
    setScriptText(saved.text);
  }

  async function uploadScript(file: File | null) {
    if (!project) {
      setMessage("Create a project first.");
      return;
    }
    if (!file) {
      return;
    }
    const uploadedScript = await client.uploadScript(project.id, file);
    setScript(uploadedScript);
    setScriptText(uploadedScript.text);
  }

  async function startJob() {
    if (!project) {
      setMessage("Create a project first.");
      return;
    }
    const started = await client.startJob(project.id, {
      voice_profile_id: voiceId,
      tts_params: ttsParams,
    });
    setJob(started);
    setQueue(await client.getQueue());
  }

  async function uploadVoice(file: File | null) {
    if (!file) {
      return;
    }
    const uploaded = await client.uploadVoice(voiceName, file);
    setVoices([...voices, uploaded]);
    setVoiceId(uploaded.id);
  }

  async function cancelJob() {
    if (!job) {
      return;
    }
    setJob(await client.cancelJob(job.id));
    setQueue(await client.getQueue());
  }

  return (
    <section className="workspace-panel">
      <Header
        eyebrow="Projects"
        title="Study Podcast Generator"
        description="Draft a study script, tune the voice, and generate a local WAV podcast."
      >
        {project && <StatusBadge value="active project" />}
      </Header>

      <div className="project-layout">
        <Panel className="project-library" label="Project library">
          <div className="section-head">
            <div>
              <h2>Project Library</h2>
              <p>{projects.length} visible projects</p>
            </div>
          </div>
          <SearchField
            label="Search projects"
            placeholder="Search projects"
            value={projectSearch}
            onChange={setProjectSearch}
          />
          <div className="create-row">
            <input value={title} onChange={(event) => setTitle(event.target.value)} aria-label="Project title" />
            <button onClick={createProject} type="button">
              <Plus aria-hidden="true" />
              Create Project
            </button>
          </div>
          <div className="project-list">
            {projects.length === 0 && <p className="empty-state">No saved projects yet.</p>}
            {projects.map((item) => (
              <button
                className={project?.id === item.id ? "project-item is-active" : "project-item"}
                aria-label={item.title}
                key={item.id}
                onClick={() => {
                  void openProject(item);
                }}
                type="button"
              >
                <span>{item.title}</span>
                <small>{formatDate(item.updated_at)}</small>
              </button>
            ))}
          </div>
        </Panel>

        <div className="project-main">
          {project && <p className="status-line">Active project: {project.title}</p>}
          <Panel className="script-panel" label="Script editor">
            <div className="section-head">
              <div>
                <h2>Script</h2>
                <p>{script?.chunks.length ?? 0} parsed chunks</p>
              </div>
              <div className="toolbar">
                <button onClick={saveScript} type="button">Save Script</button>
                <label className="file-button">
                  <Upload aria-hidden="true" />
                  Upload TXT
                  <input
                    aria-label="Upload TXT"
                    accept=".txt,text/plain"
                    type="file"
                    onChange={(event) => void uploadScript(event.target.files?.[0] ?? null)}
                  />
                </label>
                <button className="primary-button" onClick={startJob} type="button">
                  <AudioLines aria-hidden="true" />
                  Start Generation
                </button>
              </div>
            </div>
            <textarea
              id="script"
              aria-label="Script"
              value={scriptText}
              onChange={(event) => setScriptText(event.target.value)}
            />
            {message && <p className="message">{message}</p>}
          </Panel>

          <div className="editor-grid">
            {script && (
              <Panel label="Chunk preview">
                <div className="section-head">
                  <div>
                    <h2>Chunks And Speakers</h2>
                    <p>{script.speakers.join(", ") || "Narrator"}</p>
                  </div>
                </div>
                <ol className="chunk-list">
                  {script.chunks.map((chunk) => (
                    <li key={chunk.index}>
                      <strong>{chunk.speaker}</strong>
                      <span>{chunk.text}</span>
                    </li>
                  ))}
                </ol>
              </Panel>
            )}

            <Panel label="Voice and generation settings">
              <div className="section-head">
                <div>
                  <h2>Voice And Parameters</h2>
                  <p>Local Chatterbox generation controls</p>
                </div>
              </div>
              <div className="settings-grid compact">
                <label>
                  Voice
                  <select aria-label="Voice" value={voiceId} onChange={(event) => setVoiceId(event.target.value)}>
                    {voices.map((voice) => (
                      <option key={voice.id} value={voice.id}>
                        {voice.display_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Voice name
                  <input aria-label="Voice name" value={voiceName} onChange={(event) => setVoiceName(event.target.value)} />
                </label>
                <label className="file-button field-file-button">
                  <Upload aria-hidden="true" />
                  Upload Voice
                  <input
                    aria-label="Upload voice"
                    accept=".wav,.mp3,.flac,.m4a,audio/*"
                    type="file"
                    onChange={(event) => void uploadVoice(event.target.files?.[0] ?? null)}
                  />
                </label>
                {[
                  ["exaggeration", "Exaggeration"],
                  ["cfg_weight", "CFG weight"],
                  ["temperature", "Temperature"],
                  ["top_p", "Top P"],
                  ["min_p", "Min P"],
                  ["repetition_penalty", "Repetition penalty"],
                ].map(([key, label]) => (
                  <label key={key}>
                    {label}
                    <input
                      aria-label={label}
                      step={0.05}
                      type="number"
                      value={ttsParams[key as keyof typeof ttsParams]}
                      onChange={(event) =>
                        setTtsParams((existing) => ({
                          ...existing,
                          [key]: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                ))}
              </div>
            </Panel>
          </div>
        </div>

        {job && (
          <Panel className="job-progress-panel" label="Job progress">
            <div className="job-head">
              <div>
                <h2>Job Progress</h2>
                <p className="job-state-line">
                  {job.status} / {job.phase} / {job.progress_percent}%
                </p>
              </div>
              {activeJobStatuses.includes(job.status) && (
                <button className="icon-button danger-button" onClick={cancelJob} aria-label="Cancel job" type="button">
                  <XCircle aria-hidden="true" />
                </button>
              )}
            </div>
            <ProgressBar value={job.progress_percent} label="Progress percent" />
            <div className="metric-row two-up">
              <Metric label="Chunks" value={`${job.completed_chunks} / ${job.total_chunks}`} />
              <Metric label="Queue" value={queuePosition ? `#${queuePosition}` : "Ready"} />
            </div>
            <p className="sr-only">
              {job.completed_chunks} / {job.total_chunks} chunks
              {queuePosition ? ` / queue position ${queuePosition}` : ""}
            </p>
            {job.message && <p className="message">{job.message}</p>}
            {job.status === "completed" && <AudioPlayer src={audioUrl} downloadUrl={downloadUrl} />}
          </Panel>
        )}
      </div>
    </section>
  );
}

function JobsRoute({ client }: { client: ApiClient }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [queue, setQueue] = useState<QueueSummary | null>(null);
  const [message, setMessage] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [jobSearch, setJobSearch] = useState("");
  const [scriptPreview, setScriptPreview] = useState<Record<string, string>>({});

  async function refreshJobs(status = statusFilter, query = jobSearch) {
    const [jobsResult, queueResult] = await Promise.allSettled([
      client.listJobs({ status: status || undefined, q: query || undefined }),
      client.getQueue(),
    ]);
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
    void refreshJobs(statusFilter, jobSearch);
  }, [statusFilter, jobSearch]);

  async function cancelJob(jobId: string) {
    setMessage("");
    await client.cancelJob(jobId);
    await refreshJobs();
  }

  async function rerunJob(jobId: string) {
    setMessage("");
    await client.rerunJob(jobId);
    await refreshJobs();
  }

  async function inspectScript(jobId: string) {
    setMessage("");
    const script = await client.getJobScript(jobId);
    setScriptPreview((existing) => ({ ...existing, [jobId]: script.text }));
  }

  return (
    <section className="workspace-panel">
      <Header
        eyebrow="Queue"
        title="Generation Jobs"
        description="Queued, running, completed, cancelled, failed, and interrupted jobs."
      />

      <Panel label="Queue summary">
        <div className="section-head">
          <div>
            <h2>Queue Summary</h2>
            <p>Current local generation capacity</p>
          </div>
        </div>
        {queue ? (
          <div className="metric-row">
            <Metric label="Pending" value={queue.pending_count} />
            <Metric label="Running" value={queue.running_count} />
            <Metric label="Completed" value={queue.completed_count} />
            <Metric label="Max active" value={queue.max_active_jobs_total} />
          </div>
        ) : (
          <p className="empty-state">Queue summary loading.</p>
        )}
      </Panel>

      <div className="filter-bar">
        <SearchField
          label="Search jobs"
          placeholder="Search jobs, projects, messages, scripts"
          value={jobSearch}
          onChange={setJobSearch}
        />
        <SegmentedControl
          label="Job filters"
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { value: "", label: "All" },
            { value: "queued,running,cancel_requested", label: "Active" },
            { value: "completed", label: "Completed" },
            { value: "failed,cancelled,interrupted", label: "Needs attention" },
          ]}
        />
      </div>

      {message && <p className="message">{message}</p>}

      <section className="job-list" aria-label="Job history">
        {jobs.length === 0 && <p className="empty-state">No generation jobs yet.</p>}
        {jobs.map((jobItem) => (
          <JobCard
            client={client}
            inspectScript={inspectScript}
            job={jobItem}
            key={jobItem.id}
            queuePosition={queue?.queue_positions[jobItem.id] ?? null}
            rerunJob={rerunJob}
            scriptPreview={scriptPreview[jobItem.id]}
            cancelJob={cancelJob}
          />
        ))}
      </section>
    </section>
  );
}

function JobCard({
  cancelJob,
  client,
  inspectScript,
  job,
  queuePosition,
  rerunJob,
  scriptPreview,
}: {
  cancelJob(jobId: string): Promise<void>;
  client: ApiClient;
  inspectScript(jobId: string): Promise<void>;
  job: Job;
  queuePosition: number | null;
  rerunJob(jobId: string): Promise<void>;
  scriptPreview?: string;
}) {
  const canCancel = activeJobStatuses.includes(job.status);
  return (
    <article className="job-card">
      <div className="job-head">
        <div>
          <div className="job-title-row">
            <h2>{job.id}</h2>
            <StatusBadge value={job.status} />
          </div>
          <p className="job-state-line">
            {job.status} / {job.phase} / {job.progress_percent}%
          </p>
          <p>Project {job.project_id}</p>
        </div>
        {canCancel && (
          <button
            className="icon-button danger-button"
            onClick={() => {
              void cancelJob(job.id);
            }}
            aria-label={`Cancel job ${job.id}`}
            type="button"
          >
            <XCircle aria-hidden="true" />
          </button>
        )}
      </div>
      <ProgressBar value={job.progress_percent} label={`Progress for job ${job.id}`} />
      <div className="metric-row two-up">
        <Metric label="Chunks" value={`${job.completed_chunks} / ${job.total_chunks}`} />
        <Metric label="Queue" value={queuePosition ? `#${queuePosition}` : "None"} />
      </div>
      <p className="sr-only">
        {job.completed_chunks} / {job.total_chunks} chunks{queuePosition ? ` / queue position ${queuePosition}` : ""}
      </p>
      {job.current_chunk_preview && <p className="preview-line">{job.current_chunk_preview}</p>}
      {job.message && <p className="message">{job.message}</p>}
      {job.failure_reason && job.failure_reason !== job.message && <p className="message">{job.failure_reason}</p>}
      {job.snapshot && (
        <div className="snapshot-line">
          <CheckCircle2 aria-hidden="true" />
          <span>
            Voice {job.snapshot.voice_profile_id} / {Object.keys(job.snapshot.tts_params).length} TTS params /{" "}
            {job.snapshot.chunks.length} chunks
          </span>
        </div>
      )}
      <div className="toolbar">
        <button onClick={() => void inspectScript(job.id)} type="button">View script</button>
        {job.status === "completed" && <button onClick={() => void rerunJob(job.id)} type="button">Rerun</button>}
      </div>
      {scriptPreview && <pre className="script-preview">{scriptPreview}</pre>}
      {job.status === "completed" && (
        <AudioPlayer
          src={client.jobAudioStreamUrl(job.id, job.id)}
          downloadUrl={client.jobFinalAudioUrl(job.id, job.id)}
        />
      )}
    </article>
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
    <section className="workspace-panel">
      <Header
        eyebrow="Settings"
        title="TTS Settings"
        description="Chatterbox is the local TTS engine. The development test engine appears only when enabled."
      />
      {settings && (
        <>
          <Panel label="Runtime status">
            <div className="section-head">
              <div>
                <h2>Runtime</h2>
                <p>Engine reload state and active backend runtime</p>
              </div>
              <StatusBadge value={runtimeStatus} />
            </div>
            <div className="metric-row">
              <Metric label="Runtime status" value={runtimeStatus} />
              <Metric label="Active engine" value={activeEngine || "None"} />
              <Metric label="Reload required" value={reloadRequired ? "Yes" : "No"} />
            </div>
            {reloadRequired && <p className="message">Reload required</p>}
            {runtimeStatus === "ready" && <p className="status-line">Runtime ready: {activeEngine}</p>}
            {runtimeStatus !== "ready" && <p className="status-line">Runtime status: {runtimeStatus}</p>}
            {reloadError && <p className="message">{reloadError}</p>}
          </Panel>

          <Panel label="Editable settings">
            <div className="section-head">
              <div>
                <h2>Engine Controls</h2>
                <p>Changes persist to SQLite and .env</p>
              </div>
            </div>
            <div className="settings-grid">
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
            </div>
          </Panel>

          <div className="toolbar sticky-actions">
            <button className="primary-button" onClick={saveSettings} type="button">Save settings</button>
            {reloadRequired && <button onClick={reloadBackendEngine} type="button">Reload backend engine</button>}
          </div>
          {message && <p className="message">{message}</p>}
        </>
      )}
    </section>
  );
}

export function App({ client = apiClient }: AppProps) {
  const { theme, setTheme } = useThemePreference();
  return (
    <AppShell theme={theme} setTheme={setTheme}>
      <Routes>
        <Route path="/" element={<ProjectsRoute client={client} />} />
        <Route path="/jobs" element={<JobsRoute client={client} />} />
        <Route path="/settings" element={<SettingsRoute client={client} />} />
      </Routes>
    </AppShell>
  );
}
