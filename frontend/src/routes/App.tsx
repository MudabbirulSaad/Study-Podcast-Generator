import { AudioLines, FolderOpen, Settings, Timer } from "lucide-react";
import { NavLink, Route, Routes } from "react-router-dom";

function ProjectsRoute() {
  return (
    <section className="workspace-panel">
      <div>
        <p className="eyebrow">Projects</p>
        <h1>Study Podcast Generator</h1>
      </div>
      <p>Create a study project, attach one active script, and queue local WAV generation.</p>
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

function SettingsRoute() {
  return (
    <section className="workspace-panel">
      <p className="eyebrow">Settings</p>
      <h1>TTS Settings</h1>
      <p>Fake TTS is the default. Chatterbox can be enabled after local setup.</p>
    </section>
  );
}

export function App() {
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
          <Route path="/" element={<ProjectsRoute />} />
          <Route path="/projects/:projectId" element={<ProjectDetailRoute />} />
          <Route path="/jobs" element={<JobsRoute />} />
          <Route path="/settings" element={<SettingsRoute />} />
        </Routes>
      </main>
    </div>
  );
}
