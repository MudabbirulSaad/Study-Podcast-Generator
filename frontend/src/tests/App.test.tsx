import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { ApiClient } from "../api/client";
import { App } from "../routes/App";
import type { QueueSummary, TtsSettings } from "../types/api";

const queue: QueueSummary = {
  pending_count: 0,
  running_count: 0,
  completed_count: 0,
  max_active_jobs_total: 10,
  concurrency_limits: { fake: 4, chatterbox: 1, merge: 1 },
  queue_positions: {},
};

const settings: TtsSettings = {
  active_engine: "fake",
  available_engines: ["fake", "chatterbox"],
};

const client: ApiClient = {
  createProject: async () => {
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
  getQueue: async () => queue,
  getTtsSettings: async () => settings,
  finalAudioUrl: (projectId) => `/api/v1/projects/${projectId}/audio/final`,
  audioStreamUrl: (projectId) => `/api/v1/projects/${projectId}/audio/stream`,
};

describe("App", () => {
  it("renders the product name", () => {
    render(
      <MemoryRouter>
        <App />
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
});
