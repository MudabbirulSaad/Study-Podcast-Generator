import type { Job, Project, QueueSummary, RuntimeSettings, RuntimeStatus, ScriptResponse, TtsSettings } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function errorEnvelope(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return {
      code: "request_failed",
      message: "Request failed.",
      details: { status: response.status },
    };
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    throw await errorEnvelope(response);
  }
  return response.json() as Promise<T>;
}

async function uploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    body: formData,
  });
  if (!response.ok) {
    throw await errorEnvelope(response);
  }
  return response.json() as Promise<T>;
}

export type ApiClient = {
  createProject(title: string): Promise<Project>;
  saveScript(projectId: string, text: string): Promise<ScriptResponse>;
  uploadScript(projectId: string, file: File): Promise<ScriptResponse>;
  startJob(projectId: string): Promise<Job>;
  listJobs(): Promise<Job[]>;
  getJob(jobId: string): Promise<Job>;
  cancelJob(jobId: string): Promise<Job>;
  getQueue(): Promise<QueueSummary>;
  getTtsSettings(): Promise<TtsSettings>;
  getSettings(): Promise<RuntimeSettings>;
  saveSettings(values: RuntimeSettings["values"]): Promise<RuntimeSettings>;
  reloadSettings(): Promise<RuntimeStatus>;
  getRuntimeStatus(): Promise<RuntimeStatus>;
  finalAudioUrl(projectId: string, version?: string): string;
  audioStreamUrl(projectId: string, version?: string): string;
};

export const apiClient: ApiClient = {
  createProject: (title) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  saveScript: (projectId, text) =>
    request<ScriptResponse>(`/projects/${projectId}/script`, {
      method: "PUT",
      body: JSON.stringify({ text, source: "pasted" }),
    }),
  uploadScript: (projectId, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return uploadRequest<ScriptResponse>(`/projects/${projectId}/script`, formData);
  },
  startJob: (projectId) =>
    request<Job>(`/projects/${projectId}/jobs`, {
      method: "POST",
    }),
  listJobs: () => request<Job[]>("/jobs"),
  getJob: (jobId) => request<Job>(`/jobs/${jobId}`),
  cancelJob: (jobId) =>
    request<Job>(`/jobs/${jobId}/cancel`, {
      method: "POST",
    }),
  getQueue: () => request<QueueSummary>("/queue"),
  getTtsSettings: () => request<TtsSettings>("/settings/tts-engines"),
  getSettings: () => request<RuntimeSettings>("/settings"),
  saveSettings: (values) =>
    request<RuntimeSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify({ values }),
    }),
  reloadSettings: () =>
    request<RuntimeStatus>("/settings/reload", {
      method: "POST",
    }),
  getRuntimeStatus: () => request<RuntimeStatus>("/settings/runtime-status"),
  finalAudioUrl: (projectId, version) =>
    `${API_BASE}/projects/${projectId}/audio/final${version ? `?v=${encodeURIComponent(version)}` : ""}`,
  audioStreamUrl: (projectId, version) =>
    `${API_BASE}/projects/${projectId}/audio/stream${version ? `?v=${encodeURIComponent(version)}` : ""}`,
};
