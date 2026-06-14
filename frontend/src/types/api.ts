export type Project = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type Chunk = {
  index: number;
  speaker: string;
  text: string;
};

export type ScriptResponse = {
  project_id: string;
  text: string;
  source: "pasted" | "uploaded";
  speakers: string[];
  updated_at: string;
  chunks: Chunk[];
};

export type Job = {
  id: string;
  project_id: string;
  status: string;
  phase: string;
  progress_percent: number;
  total_chunks: number;
  completed_chunks: number;
  current_chunk_index: number | null;
  current_chunk_preview: string | null;
  message: string;
  failure_reason: string | null;
  cancellation_requested: boolean;
  created_at: string;
  started_at: string | null;
  updated_at: string;
  completed_at: string | null;
};

export type QueueSummary = {
  pending_count: number;
  running_count: number;
  completed_count: number;
  max_active_jobs_total: number;
  concurrency_limits: Record<string, number>;
  queue_positions: Record<string, number>;
};

export type TtsSettings = {
  active_engine: string;
  available_engines: string[];
};

export type RuntimeSettings = {
  values: Record<string, string | number | boolean>;
  editable_fields: string[];
  available_engines: string[];
  reload_required: boolean;
  runtime_status: string;
  last_reload_error: string | null;
};

export type RuntimeStatus = {
  status: string;
  active_engine: string;
  reload_required: boolean;
  last_reload_error: string | null;
};
