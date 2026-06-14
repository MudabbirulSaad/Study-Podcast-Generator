from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from study_podcast.domain.entities import (
    ActivePodcastScript,
    GenerationJob,
    QueueSummary,
    StudyProject,
    TextChunk,
)


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None = None


class CreateProjectRequest(BaseModel):
    title: str


class ProjectResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, project: StudyProject) -> "ProjectResponse":
        return cls.model_validate(project, from_attributes=True)


class ProjectDetailResponse(ProjectResponse):
    has_active_script: bool
    latest_jobs: list["JobResponse"]


class SaveScriptRequest(BaseModel):
    text: str
    source: Literal["pasted", "uploaded"] = "pasted"


class ChunkResponse(BaseModel):
    index: int
    speaker: str
    text: str

    @classmethod
    def from_domain(cls, chunk: TextChunk) -> "ChunkResponse":
        return cls.model_validate(chunk, from_attributes=True)


class ScriptResponse(BaseModel):
    project_id: str
    text: str
    source: str
    speakers: list[str]
    updated_at: datetime
    chunks: list[ChunkResponse]

    @classmethod
    def from_domain(cls, script: ActivePodcastScript, chunks: list[TextChunk]) -> "ScriptResponse":
        return cls(
            project_id=script.project_id,
            text=script.text,
            source=script.source.value,
            speakers=list(script.speakers),
            updated_at=script.updated_at,
            chunks=[ChunkResponse.from_domain(chunk) for chunk in chunks],
        )


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    status: str
    phase: str
    progress_percent: int
    total_chunks: int
    completed_chunks: int
    current_chunk_index: int | None
    current_chunk_preview: str | None
    message: str
    failure_reason: str | None
    cancellation_requested: bool
    created_at: datetime
    started_at: datetime | None
    updated_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_domain(cls, job: GenerationJob) -> "JobResponse":
        return cls.model_validate(job, from_attributes=True)


class QueueResponse(BaseModel):
    pending_count: int
    running_count: int
    completed_count: int
    max_active_jobs_total: int
    concurrency_limits: dict[str, int]
    queue_positions: dict[str, int]

    @classmethod
    def from_domain(cls, summary: QueueSummary) -> "QueueResponse":
        return cls.model_validate(summary, from_attributes=True)


class TtsEngineSettingsResponse(BaseModel):
    active_engine: str
    available_engines: list[str]


class UpdateTtsEngineRequest(BaseModel):
    engine: str


class RuntimeSettingsResponse(BaseModel):
    values: dict[str, object]
    editable_fields: list[str]
    available_engines: list[str]
    reload_required: bool
    runtime_status: str
    last_reload_error: str | None


class UpdateRuntimeSettingsRequest(BaseModel):
    values: dict[str, object]


class RuntimeStatusResponse(BaseModel):
    status: str
    active_engine: str
    reload_required: bool
    last_reload_error: str | None
