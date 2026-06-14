import type { Job, Project, QueueSummary, ScriptResponse, TtsSettings } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    throw await response.json();
  }
  return response.json() as Promise<T>;
}

async function uploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    body: formData,
  });
  if (!response.ok) {
    throw await response.json();
  }
  return response.json() as Promise<T>;
}

export type ApiClient = {
  createProject(title: string): Promise<Project>;
  saveScript(projectId: string, text: string): Promise<ScriptResponse>;
  uploadScript(projectId: string, file: File): Promise<ScriptResponse>;
  startJob(projectId: string): Promise<Job>;
  getJob(jobId: string): Promise<Job>;
  cancelJob(jobId: string): Promise<Job>;
  getQueue(): Promise<QueueSummary>;
  getTtsSettings(): Promise<TtsSettings>;
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
  getJob: (jobId) => request<Job>(`/jobs/${jobId}`),
  cancelJob: (jobId) =>
    request<Job>(`/jobs/${jobId}/cancel`, {
      method: "POST",
    }),
  getQueue: () => request<QueueSummary>("/queue"),
  getTtsSettings: () => request<TtsSettings>("/settings/tts-engines"),
};
