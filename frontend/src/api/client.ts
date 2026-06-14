import type {
  Job,
  Project,
  ProjectDetail,
  QueueSummary,
  RuntimeSettings,
  RuntimeStatus,
  ScriptResponse,
  StartJobInput,
  TtsSettings,
  VoiceProfile,
} from "../types/api";

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

async function postUploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw await errorEnvelope(response);
  }
  return response.json() as Promise<T>;
}

export type ApiClient = {
  createProject(title: string): Promise<Project>;
  listProjects(): Promise<Project[]>;
  getProject(projectId: string): Promise<ProjectDetail>;
  getScript(projectId: string): Promise<ScriptResponse>;
  saveScript(projectId: string, text: string): Promise<ScriptResponse>;
  uploadScript(projectId: string, file: File): Promise<ScriptResponse>;
  startJob(projectId: string, input?: StartJobInput): Promise<Job>;
  listJobs(filters?: { status?: string; projectId?: string }): Promise<Job[]>;
  getJob(jobId: string): Promise<Job>;
  cancelJob(jobId: string): Promise<Job>;
  rerunJob(jobId: string): Promise<Job>;
  getJobScript(jobId: string): Promise<ScriptResponse>;
  listVoices(): Promise<VoiceProfile[]>;
  uploadVoice(displayName: string, file: File): Promise<VoiceProfile>;
  getQueue(): Promise<QueueSummary>;
  getTtsSettings(): Promise<TtsSettings>;
  getSettings(): Promise<RuntimeSettings>;
  saveSettings(values: RuntimeSettings["values"]): Promise<RuntimeSettings>;
  reloadSettings(): Promise<RuntimeStatus>;
  getRuntimeStatus(): Promise<RuntimeStatus>;
  finalAudioUrl(projectId: string, version?: string): string;
  audioStreamUrl(projectId: string, version?: string): string;
  jobFinalAudioUrl(jobId: string, version?: string): string;
  jobAudioStreamUrl(jobId: string, version?: string): string;
};

export const apiClient: ApiClient = {
  createProject: (title) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  listProjects: () => request<Project[]>("/projects"),
  getProject: (projectId) => request<ProjectDetail>(`/projects/${projectId}`),
  getScript: (projectId) => request<ScriptResponse>(`/projects/${projectId}/script`),
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
  startJob: (projectId, input) =>
    request<Job>(`/projects/${projectId}/jobs`, {
      method: "POST",
      body: JSON.stringify(input ?? {}),
    }),
  listJobs: (filters) => {
    const params = new URLSearchParams();
    if (filters?.status) {
      params.set("status", filters.status);
    }
    if (filters?.projectId) {
      params.set("project_id", filters.projectId);
    }
    const query = params.toString();
    return request<Job[]>(`/jobs${query ? `?${query}` : ""}`);
  },
  getJob: (jobId) => request<Job>(`/jobs/${jobId}`),
  cancelJob: (jobId) =>
    request<Job>(`/jobs/${jobId}/cancel`, {
      method: "POST",
    }),
  rerunJob: (jobId) =>
    request<Job>(`/jobs/${jobId}/rerun`, {
      method: "POST",
    }),
  getJobScript: (jobId) => request<ScriptResponse>(`/jobs/${jobId}/script`),
  listVoices: () => request<VoiceProfile[]>("/voices"),
  uploadVoice: (displayName, file) => {
    const formData = new FormData();
    formData.append("display_name", displayName);
    formData.append("file", file);
    return postUploadRequest<VoiceProfile>("/voices", formData);
  },
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
  jobFinalAudioUrl: (jobId, version) =>
    `${API_BASE}/jobs/${jobId}/audio/final${version ? `?v=${encodeURIComponent(version)}` : ""}`,
  jobAudioStreamUrl: (jobId, version) =>
    `${API_BASE}/jobs/${jobId}/audio/stream${version ? `?v=${encodeURIComponent(version)}` : ""}`,
};
