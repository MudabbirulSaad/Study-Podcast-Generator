import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../api/client";

describe("apiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("defaults to same-origin api URLs for production-style serving", () => {
    expect(apiClient.finalAudioUrl("project-1")).toBe("/api/v1/projects/project-1/audio/final");
    expect(apiClient.audioStreamUrl("project-1")).toBe("/api/v1/projects/project-1/audio/stream");
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
