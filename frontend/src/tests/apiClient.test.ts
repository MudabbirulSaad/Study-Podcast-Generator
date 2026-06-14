import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../api/client";

describe("apiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("defaults to same-origin api URLs for production-style serving", () => {
    expect(apiClient.finalAudioUrl("project-1")).toBe("/api/v1/projects/project-1/audio/final");
    expect(apiClient.audioStreamUrl("project-1")).toBe("/api/v1/projects/project-1/audio/stream");
    expect(apiClient.finalAudioUrl("project-1", "job 1")).toBe(
      "/api/v1/projects/project-1/audio/final?v=job%201",
    );
    expect(apiClient.audioStreamUrl("project-1", "job 1")).toBe(
      "/api/v1/projects/project-1/audio/stream?v=job%201",
    );
    expect(apiClient.jobFinalAudioUrl("job-1", "job 1")).toBe(
      "/api/v1/jobs/job-1/audio/final?v=job%201",
    );
    expect(apiClient.jobAudioStreamUrl("job-1", "job 1")).toBe(
      "/api/v1/jobs/job-1/audio/stream?v=job%201",
    );
  });

  it("sends job list filters as query parameters", async () => {
    const fetchMock = vi.fn(
      async () => new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiClient.listJobs({ status: "completed", projectId: "project-1" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/jobs?status=completed&project_id=project-1",
      expect.any(Object),
    );
  });

  it("throws a stable envelope for non-json error responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("Internal Server Error", { status: 500 })),
    );

    await expect(apiClient.listJobs()).rejects.toEqual({
      code: "request_failed",
      message: "Request failed.",
      details: { status: 500 },
    });
  });
});
