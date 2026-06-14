import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { ApiClient } from "../api/client";
import { App } from "../routes/App";
import type {
  Job,
  Project,
  QueueSummary,
  RuntimeSettings,
  RuntimeStatus,
  ScriptResponse,
  TtsSettings,
  VoiceProfile,
} from "../types/api";

const now = "2026-06-14T00:00:00Z";

function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: "job-1",
    project_id: "project-1",
    status: "queued",
    phase: "queued",
    progress_percent: 0,
    total_chunks: 2,
    completed_chunks: 0,
    current_chunk_index: null,
    current_chunk_preview: null,
    message: "Queued",
    failure_reason: null,
    cancellation_requested: false,
    created_at: now,
    started_at: null,
    updated_at: now,
    completed_at: null,
    ...overrides,
  };
}

function makeClient(): ApiClient {
  const project: Project = {
    id: "project-1",
    title: "Biology 101",
    created_at: now,
    updated_at: now,
  };
  const script: ScriptResponse = {
    project_id: "project-1",
    text: "[S1] Cells divide.",
    source: "pasted",
    speakers: ["S1", "Narrator"],
    updated_at: now,
    chunks: [
      { index: 0, speaker: "S1", text: "Cells divide." },
      { index: 1, speaker: "Narrator", text: "Tissues grow." },
    ],
  };
  const queue: QueueSummary = {
    pending_count: 1,
    running_count: 0,
    completed_count: 0,
    max_active_jobs_total: 10,
    concurrency_limits: { fake: 4, chatterbox: 1, merge: 1 },
    queue_positions: { "job-1": 1 },
  };
  const settings: TtsSettings = {
    active_engine: "chatterbox",
    available_engines: ["chatterbox"],
  };
  const voices: VoiceProfile[] = [
    {
      id: "default",
      display_name: "Default Chatterbox voice",
      source: "default",
      sample_path: null,
      created_at: now,
      updated_at: now,
    },
  ];
  const runtimeSettings: RuntimeSettings = {
    values: {
      active_tts_engine: "chatterbox",
      chatterbox_device: "auto",
      max_script_size_bytes: 1000000,
      max_chunk_chars: 600,
      max_chunks: 1000,
      chatterbox_max_concurrent_jobs: 1,
      audio_merge_max_concurrent_jobs: 1,
      max_active_jobs_total: 10,
      storage_root: "data/storage",
      frontend_origin: "http://localhost:5173",
      serve_frontend: true,
    },
    editable_fields: [
      "active_tts_engine",
      "chatterbox_device",
      "max_chunk_chars",
      "max_chunks",
      "chatterbox_max_concurrent_jobs",
    ],
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
  return {
    createProject: async () => project,
    listProjects: async () => [project],
    getProject: async () => ({
      ...project,
      has_active_script: true,
      latest_jobs: [],
    }),
    getScript: async () => script,
    saveScript: async () => script,
    startJob: async (_projectId, input) =>
      makeJob({
        snapshot: {
          job_id: "job-1",
          project_id: "project-1",
          script_text: script.text,
          script_source: "pasted",
          speakers: script.speakers,
          chunks: script.chunks,
          voice_profile_id: input?.voice_profile_id ?? "default",
          tts_params: input?.tts_params ?? {},
          created_at: now,
        },
      }),
    listJobs: async () => [
      makeJob({
        id: "job-1",
        status: "completed",
        phase: "completed",
        progress_percent: 100,
        completed_chunks: 2,
        message: "Completed",
      }),
      makeJob({
        id: "job-2",
        project_id: "project-2",
        status: "failed",
        phase: "synthesizing",
        progress_percent: 45,
        completed_chunks: 1,
        message: "script not found",
        failure_reason: "script not found",
      }),
    ],
    getJob: async () => makeJob({ status: "running", phase: "synthesizing", progress_percent: 45 }),
    cancelJob: async () => makeJob({ status: "cancelled", message: "Cancelled" }),
    rerunJob: async () => makeJob({ id: "job-rerun" }),
    getJobScript: async () => script,
    listVoices: async () => voices,
    uploadVoice: async () => ({
      id: "voice-1",
      display_name: "My seminar voice",
      source: "uploaded",
      sample_path: "storage/voices/voice-1/sample.wav",
      created_at: now,
      updated_at: now,
    }),
    uploadScript: async () => script,
    getQueue: async () => queue,
    getTtsSettings: async () => settings,
    getSettings: async () => runtimeSettings,
    saveSettings: async (values) => ({
      ...runtimeSettings,
      values: { ...runtimeSettings.values, ...values },
      reload_required: true,
      runtime_status: "reload_pending",
    }),
    reloadSettings: async () => runtimeStatus,
    getRuntimeStatus: async () => runtimeStatus,
    finalAudioUrl: (projectId, version) =>
      `http://api.test/api/v1/projects/${projectId}/audio/final${version ? `?v=${version}` : ""}`,
    audioStreamUrl: (projectId, version) =>
      `http://api.test/api/v1/projects/${projectId}/audio/stream${version ? `?v=${version}` : ""}`,
    jobFinalAudioUrl: (jobId, version) =>
      `http://api.test/api/v1/jobs/${jobId}/audio/final${version ? `?v=${version}` : ""}`,
    jobAudioStreamUrl: (jobId, version) =>
      `http://api.test/api/v1/jobs/${jobId}/audio/stream${version ? `?v=${version}` : ""}`,
  };
}

describe("workflow UI", () => {
  it("loads persisted projects and opens an existing script", async () => {
    render(
      <MemoryRouter>
        <App client={makeClient()} />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Project Library" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Biology 101" })).toBeInTheDocument();
    expect(await screen.findByText("Active project: Biology 101")).toBeInTheDocument();
    expect(screen.getByDisplayValue("[S1] Cells divide.")).toBeInTheDocument();
  });

  it("creates a project, previews chunks, starts and cancels a job", async () => {
    render(
      <MemoryRouter>
        <App client={makeClient()} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create Project" }));
    expect(await screen.findByText("Active project: Biology 101")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Save Script" }));
    expect(await screen.findByRole("heading", { name: "Chunks And Speakers" })).toBeInTheDocument();
    expect(screen.getByText("Cells divide.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start Generation" }));
    expect(await screen.findByRole("heading", { name: "Job Progress" })).toBeInTheDocument();
    expect(screen.getByText("queued / queued / 0%")).toBeInTheDocument();
    expect(screen.getByText(/queue position 1/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cancel job" }));
    await waitFor(() => expect(screen.getByText("cancelled / queued / 0%")).toBeInTheDocument());
    expect(screen.getByText("Cancelled")).toBeInTheDocument();
  });

  it("selects and uploads reusable voices before generation", async () => {
    const client = makeClient();
    render(
      <MemoryRouter>
        <App client={client} />
      </MemoryRouter>,
    );

    expect(await screen.findByLabelText("Voice")).toHaveValue("default");
    const file = new File(["RIFFvoice"], "voice.wav", { type: "audio/wav" });
    fireEvent.change(screen.getByLabelText("Upload voice"), { target: { files: [file] } });
    expect(await screen.findByRole("option", { name: "My seminar voice" })).toBeInTheDocument();
    expect(screen.getByLabelText("Voice")).toHaveValue("voice-1");
  });

  it("shows playback and download controls for a completed job", async () => {
    const client = makeClient();
    client.startJob = async () =>
      makeJob({ status: "completed", phase: "completed", progress_percent: 100, completed_chunks: 2 });

    render(
      <MemoryRouter>
        <App client={client} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create Project" }));
    await screen.findByText("Active project: Biology 101");
    fireEvent.click(screen.getByRole("button", { name: "Start Generation" }));

    expect(await screen.findByText("completed / completed / 100%")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download WAV" })).toHaveAttribute(
      "href",
      "http://api.test/api/v1/jobs/job-1/audio/final?v=job-1",
    );
    expect(screen.getByLabelText("Custom audio player")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open Stream" })).not.toBeInTheDocument();
  });

  it("uses the completed job id to refresh the audio player after regeneration", async () => {
    let generationCount = 0;
    const client = makeClient();
    client.startJob = async () => {
      generationCount += 1;
      return makeJob({
        id: `job-${generationCount}`,
        status: "completed",
        phase: "completed",
        progress_percent: 100,
        completed_chunks: 2,
      });
    };

    render(
      <MemoryRouter>
        <App client={client} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create Project" }));
    await screen.findByText("Active project: Biology 101");

    fireEvent.click(screen.getByRole("button", { name: "Start Generation" }));
    const firstAudio = await screen.findByLabelText("Generated podcast audio source");
    expect(firstAudio).toHaveAttribute(
      "src",
      "http://api.test/api/v1/jobs/job-1/audio/stream?v=job-1",
    );

    fireEvent.click(screen.getByRole("button", { name: "Start Generation" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Generated podcast audio source")).toHaveAttribute(
        "src",
        "http://api.test/api/v1/jobs/job-2/audio/stream?v=job-2",
      ),
    );
  });

  it("renders job history on the jobs route", async () => {
    render(
      <MemoryRouter initialEntries={["/jobs"]}>
        <App client={makeClient()} />
      </MemoryRouter>,
    );

    expect(await screen.findByText("job-1")).toBeInTheDocument();
    expect(screen.getByText("completed / completed / 100%")).toBeInTheDocument();
    expect(screen.getByText("2 / 2 chunks / queue position 1")).toBeInTheDocument();
    expect(screen.getByText("job-2")).toBeInTheDocument();
    expect(screen.getByText("failed / synthesizing / 45%")).toBeInTheDocument();
    expect(screen.getAllByText("script not found")).toHaveLength(1);
  });

  it("filters jobs, inspects scripts, and reruns completed jobs", async () => {
    const client = makeClient();
    render(
      <MemoryRouter initialEntries={["/jobs"]}>
        <App client={client} />
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Completed" }));
    expect(await screen.findByText("job-1")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "View script" })[0]);
    expect(await screen.findByText("[S1] Cells divide.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Rerun" }));
    await waitFor(() => expect(screen.getByText("job-1")).toBeInTheDocument());
  });

  it("keeps job history visible when queue summary fails", async () => {
    const client = makeClient();
    client.getQueue = async () => {
      throw { code: "request_failed", message: "Request failed." };
    };

    render(
      <MemoryRouter initialEntries={["/jobs"]}>
        <App client={client} />
      </MemoryRouter>,
    );

    expect(await screen.findByText("job-1")).toBeInTheDocument();
    expect(screen.getByText("Queue summary unavailable.")).toBeInTheDocument();
  });

  it("saves runtime settings and reloads the backend engine", async () => {
    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <App client={makeClient()} />
      </MemoryRouter>,
    );

    expect(await screen.findByLabelText("TTS engine")).toHaveValue("chatterbox");
    fireEvent.change(screen.getByLabelText("Chatterbox device"), { target: { value: "cpu" } });
    fireEvent.change(screen.getByLabelText("Max chunk chars"), { target: { value: "320" } });
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    expect(await screen.findByText("Reload required")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reload backend engine" }));
    expect(await screen.findByText("Runtime ready: chatterbox")).toBeInTheDocument();
  });

  it("shows runtime reload failures on the settings page", async () => {
    const client = makeClient();
    client.reloadSettings = async () => ({
      status: "failed",
      active_engine: "chatterbox",
      reload_required: true,
      last_reload_error: "model load failed",
    });

    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <App client={client} />
      </MemoryRouter>,
    );

    await screen.findByLabelText("TTS engine");
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
    fireEvent.click(await screen.findByRole("button", { name: "Reload backend engine" }));

    expect(await screen.findByText("model load failed")).toBeInTheDocument();
  });
});
