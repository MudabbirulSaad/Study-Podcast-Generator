import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import type { ApiClient } from "../api/client";
import { App } from "../routes/App";
import type { QueueSummary, RuntimeSettings, RuntimeStatus, TtsSettings } from "../types/api";

const queue: QueueSummary = {
  pending_count: 0,
  running_count: 0,
  completed_count: 0,
  max_active_jobs_total: 10,
  concurrency_limits: { fake: 4, chatterbox: 1, merge: 1 },
  queue_positions: {},
};

const settings: TtsSettings = {
  active_engine: "chatterbox",
  available_engines: ["chatterbox"],
};

const runtimeSettings: RuntimeSettings = {
  values: {
    active_tts_engine: "chatterbox",
    chatterbox_device: "auto",
    max_chunk_chars: 600,
  },
  editable_fields: ["active_tts_engine", "chatterbox_device", "max_chunk_chars"],
  available_engines: ["chatterbox"],
  reload_required: false,
  runtime_status: "idle",
  last_reload_error: null,
};

const runtimeStatus: RuntimeStatus = {
  status: "ready",
  active_engine: "chatterbox",
  reload_required: false,
  last_reload_error: null,
};

const client: ApiClient = {
  createProject: async () => {
    throw new Error("not used");
  },
  listProjects: async () => [],
  getProject: async () => {
    throw new Error("not used");
  },
  getScript: async () => {
    throw new Error("not used");
  },
  saveScript: async () => {
    throw new Error("not used");
  },
  uploadScript: async () => {
    throw new Error("not used");
  },
  startJob: async () => {
    throw new Error("not used");
  },
  listJobs: async () => [],
  getJob: async () => {
    throw new Error("not used");
  },
  cancelJob: async () => {
    throw new Error("not used");
  },
  rerunJob: async () => {
    throw new Error("not used");
  },
  getJobScript: async () => {
    throw new Error("not used");
  },
  listVoices: async () => [],
  uploadVoice: async () => {
    throw new Error("not used");
  },
  getQueue: async () => queue,
  getTtsSettings: async () => settings,
  getSettings: async () => runtimeSettings,
  saveSettings: async () => runtimeSettings,
  reloadSettings: async () => runtimeStatus,
  getRuntimeStatus: async () => runtimeStatus,
  finalAudioUrl: (projectId, version) =>
    `/api/v1/projects/${projectId}/audio/final${version ? `?v=${version}` : ""}`,
  audioStreamUrl: (projectId, version) =>
    `/api/v1/projects/${projectId}/audio/stream${version ? `?v=${version}` : ""}`,
  jobFinalAudioUrl: (jobId, version) =>
    `/api/v1/jobs/${jobId}/audio/final${version ? `?v=${version}` : ""}`,
  jobAudioStreamUrl: (jobId, version) =>
    `/api/v1/jobs/${jobId}/audio/stream${version ? `?v=${version}` : ""}`,
};

describe("App", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("renders the product name", () => {
    render(
      <MemoryRouter>
        <App client={client} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Study Podcast Generator" })).toBeInTheDocument();
  });

  it("renders the jobs route", () => {
    render(
      <MemoryRouter initialEntries={["/jobs"]}>
        <App client={client} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Generation Jobs" })).toBeInTheDocument();
  });

  it("persists the selected theme", () => {
    render(
      <MemoryRouter>
        <App client={client} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Theme: system" }));

    expect(window.localStorage.getItem("studycast-theme")).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
