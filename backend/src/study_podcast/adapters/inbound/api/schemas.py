from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from study_podcast.domain.entities import (
    ActivePodcastScript,
    GenerationJob,
    JobInputSnapshot,
    QueueSummary,
    StudyProject,
    TextChunk,
    VoiceProfile,
)
from study_podcast.domain.value_objects import JobPhase, JobStatus, ScriptSource

ProjectId = Annotated[
    str,
    Field(
        description="App-generated project UUID string.",
        json_schema_extra={"format": "uuid"},
    ),
]
JobId = Annotated[
    str,
    Field(
        description="App-generated job UUID string.",
        json_schema_extra={"format": "uuid"},
    ),
]
VoiceProfileId = Annotated[
    str,
    Field(description='Voice profile identifier. The built-in default voice uses "default".'),
]
RuntimeSettingValue = str | int | bool
RuntimeStatus = Literal["idle", "reload_pending", "reloading", "ready", "failed"]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(ge=1)]
ProgressPercent = Annotated[int, Field(ge=0, le=100)]
ChunkPreview = Annotated[str, Field(json_schema_extra={"maxLength": 120})]


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None


def error_response(
    description: str,
    examples: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {"application/json": {"examples": examples}},
    }


def error_example(
    *,
    summary: str,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "summary": summary,
        "value": {
            "code": code,
            "message": message,
            "details": details,
        },
    }


BAD_REQUEST_RESPONSE = {
    "model": ErrorResponse,
    "description": "Bad Request",
    "content": {
        "application/json": {
            "examples": {
                "domain_error": {
                    "summary": "Domain validation error",
                    "value": {
                        "code": "domain_error",
                        "message": "script text is required",
                        "details": None,
                    },
                }
            }
        }
    },
}
NOT_FOUND_RESPONSE = {
    "model": ErrorResponse,
    "description": "Not Found",
    "content": {
        "application/json": {
            "examples": {
                "not_found": {
                    "summary": "Resource not found",
                    "value": {
                        "code": "not_found",
                        "message": "job not found",
                        "details": None,
                    },
                }
            }
        }
    },
}
CONFLICT_RESPONSE = {
    "model": ErrorResponse,
    "description": "Conflict",
    "content": {
        "application/json": {
            "examples": {
                "active_job_exists": {
                    "summary": "Project already has an active job",
                    "value": {
                        "code": "active_job_exists",
                        "message": "This project already has an active generation job.",
                        "details": {"job_id": "00000000-0000-0000-0000-000000000000"},
                    },
                }
            }
        }
    },
}


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(json_schema_extra={"minLength": 1})


class ProjectResponse(BaseModel):
    id: ProjectId
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
    model_config = ConfigDict(extra="forbid")

    text: str = Field(json_schema_extra={"minLength": 1})
    source: ScriptSource = ScriptSource.PASTED


class StartJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voice_profile_id: VoiceProfileId = "default"
    tts_params: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Engine-specific numeric TTS parameters passed through to the active engine. "
            "Unknown keys are not validated by the API."
        ),
        examples=[{"temperature": 0.4, "cfg_weight": 0.7}],
    )


class ChunkResponse(BaseModel):
    index: NonNegativeInt
    speaker: str
    text: str

    @classmethod
    def from_domain(cls, chunk: TextChunk) -> "ChunkResponse":
        return cls.model_validate(chunk, from_attributes=True)


class ScriptResponse(BaseModel):
    project_id: ProjectId
    text: str
    source: ScriptSource
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

    id: JobId
    project_id: ProjectId
    status: JobStatus
    phase: JobPhase
    progress_percent: ProgressPercent
    total_chunks: NonNegativeInt
    completed_chunks: NonNegativeInt
    current_chunk_index: NonNegativeInt | None
    current_chunk_preview: ChunkPreview | None
    message: str
    failure_reason: str | None
    cancellation_requested: bool
    created_at: datetime
    started_at: datetime | None
    updated_at: datetime
    completed_at: datetime | None
    snapshot: "JobSnapshotResponse | None" = None

    @classmethod
    def from_domain(
        cls,
        job: GenerationJob,
        snapshot: JobInputSnapshot | None = None,
    ) -> "JobResponse":
        response = cls.model_validate(job, from_attributes=True)
        response.snapshot = (
            JobSnapshotResponse.from_domain(snapshot) if snapshot is not None else None
        )
        return response


class JobSnapshotResponse(BaseModel):
    job_id: JobId
    project_id: ProjectId
    script_text: str
    script_source: ScriptSource
    speakers: list[str]
    chunks: list[ChunkResponse]
    voice_profile_id: VoiceProfileId
    tts_params: dict[str, float]
    created_at: datetime

    @classmethod
    def from_domain(cls, snapshot: JobInputSnapshot) -> "JobSnapshotResponse":
        return cls(
            job_id=snapshot.job_id,
            project_id=snapshot.project_id,
            script_text=snapshot.script_text,
            script_source=snapshot.script_source.value,
            speakers=list(snapshot.speakers),
            chunks=[ChunkResponse.from_domain(chunk) for chunk in snapshot.chunks],
            voice_profile_id=snapshot.voice_profile_id,
            tts_params=snapshot.tts_params,
            created_at=snapshot.created_at,
        )


class QueueResponse(BaseModel):
    pending_count: NonNegativeInt
    running_count: NonNegativeInt
    completed_count: NonNegativeInt
    max_active_jobs_total: PositiveInt
    concurrency_limits: dict[str, NonNegativeInt]
    queue_positions: dict[str, NonNegativeInt]

    @classmethod
    def from_domain(cls, summary: QueueSummary) -> "QueueResponse":
        return cls.model_validate(summary, from_attributes=True)


class TtsEngineSettingsResponse(BaseModel):
    active_engine: str
    available_engines: list[str]


class UpdateTtsEngineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str


class RuntimeSettingsValuesResponse(BaseModel):
    active_tts_engine: str
    chatterbox_device: str
    max_script_size_bytes: int
    max_chunk_chars: int
    max_chunks: int
    chatterbox_max_concurrent_jobs: int
    audio_merge_max_concurrent_jobs: int
    max_active_jobs_total: int
    storage_root: str
    frontend_origin: str
    serve_frontend: bool

    @model_validator(mode="before")
    @classmethod
    def serialize_path_values(cls, value):
        if not isinstance(value, dict):
            return value
        return {key: str(item) if isinstance(item, Path) else item for key, item in value.items()}


class RuntimeSettingsResponse(BaseModel):
    values: RuntimeSettingsValuesResponse
    editable_fields: list[str]
    available_engines: list[str]
    reload_required: bool
    runtime_status: RuntimeStatus
    last_reload_error: str | None


class UpdateRuntimeSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, RuntimeSettingValue] = Field(
        description=(
            "Runtime settings to update. Keys must be editable settings; values must be "
            "string, integer, or boolean scalars."
        ),
        examples=[
            {
                "active_tts_engine": "fake",
                "max_chunk_chars": 320,
                "serve_frontend": False,
            }
        ],
    )


class RuntimeStatusResponse(BaseModel):
    status: RuntimeStatus
    active_engine: str
    reload_required: bool
    last_reload_error: str | None


class VoiceProfileResponse(BaseModel):
    id: VoiceProfileId
    display_name: str
    source: str
    sample_path: str | None = Field(
        description=(
            "Deprecated legacy local storage path for the uploaded sample. "
            "Clients should use has_sample instead."
        ),
        deprecated=True,
    )
    has_sample: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, profile: VoiceProfile) -> "VoiceProfileResponse":
        return cls(
            id=profile.id,
            display_name=profile.display_name,
            source=profile.source,
            sample_path=profile.sample_path,
            has_sample=profile.sample_path is not None,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
