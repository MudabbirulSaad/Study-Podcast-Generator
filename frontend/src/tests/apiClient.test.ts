import { describe, expect, it } from "vitest";

import { apiClient } from "../api/client";

describe("apiClient", () => {
  it("defaults to same-origin api URLs for production-style serving", () => {
    expect(apiClient.finalAudioUrl("project-1")).toBe("/api/v1/projects/project-1/audio/final");
    expect(apiClient.audioStreamUrl("project-1")).toBe("/api/v1/projects/project-1/audio/stream");
  });
});
