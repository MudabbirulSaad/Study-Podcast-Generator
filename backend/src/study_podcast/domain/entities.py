from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from study_podcast.domain.value_objects import JobPhase, JobStatus, ScriptSource


@dataclass(frozen=True)
class StudyProject:
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, title: str, now: datetime) -> "StudyProject":
        return cls(id=str(uuid4()), title=title.strip(), created_at=now, updated_at=now)


@dataclass(frozen=True)
class ActivePodcastScript:
    project_id: str
    text: str
    source: ScriptSource
    speakers: tuple[str, ...]
    updated_at: datetime


@dataclass(frozen=True)
class SpeakerSegment:
    speaker: str
    text: str


@dataclass(frozen=True)
class TextChunk:
    index: int
    speaker: str
    text: str


@dataclass(frozen=True)
class JobInputSnapshot:
    job_id: str
    project_id: str
    script_text: str
    script_source: ScriptSource
    speakers: tuple[str, ...]
    chunks: tuple[TextChunk, ...]
    voice_profile_id: str
    tts_params: dict[str, float]
    created_at: datetime


@dataclass(frozen=True)
class VoiceProfile:
    id: str
    display_name: str
    source: str
    sample_path: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def default(cls, now: datetime) -> "VoiceProfile":
        return cls(
            id="default",
            display_name="Default Chatterbox voice",
            source="default",
            sample_path=None,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def uploaded(
        cls,
        *,
        display_name: str,
        sample_path: str,
        now: datetime,
    ) -> "VoiceProfile":
        return cls(
            id=str(uuid4()),
            display_name=display_name.strip(),
            source="uploaded",
            sample_path=sample_path,
            created_at=now,
            updated_at=now,
        )


@dataclass
class GenerationJob:
    id: str
    project_id: str
    status: JobStatus
    phase: JobPhase
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
    def create(cls, project_id: str, created_at: datetime) -> "GenerationJob":
        return cls(
            id=str(uuid4()),
            project_id=project_id,
            status=JobStatus.QUEUED,
            phase=JobPhase.QUEUED,
            progress_percent=0,
            total_chunks=0,
            completed_chunks=0,
            current_chunk_index=None,
            current_chunk_preview=None,
            message="Queued",
            failure_reason=None,
            cancellation_requested=False,
            created_at=created_at,
            started_at=None,
            updated_at=created_at,
            completed_at=None,
        )

    def mark_running(self, now: datetime) -> None:
        self.status = JobStatus.RUNNING
        self.started_at = self.started_at or now
        self.updated_at = now
        self.message = "Running"

    def set_chunking(self, total_chunks: int, now: datetime) -> None:
        self.phase = JobPhase.CHUNKING
        self.total_chunks = total_chunks
        self.progress_percent = 5 if total_chunks else 0
        self.updated_at = now
        self.message = "Chunking script"

    def record_chunk_progress(
        self,
        completed_chunks: int,
        current_chunk_index: int,
        current_chunk_preview: str,
        now: datetime,
    ) -> None:
        self.phase = JobPhase.SYNTHESIZING
        self.completed_chunks = completed_chunks
        self.current_chunk_index = current_chunk_index
        self.current_chunk_preview = current_chunk_preview[:120]
        if self.total_chunks:
            self.progress_percent = min(90, int((completed_chunks / self.total_chunks) * 90))
        self.updated_at = now
        self.message = "Synthesizing audio"

    def request_cancellation(self, now: datetime) -> None:
        self.status = JobStatus.CANCEL_REQUESTED
        self.cancellation_requested = True
        self.updated_at = now
        self.message = "Cancellation requested"

    def mark_cancelled(self, now: datetime) -> None:
        self.status = JobStatus.CANCELLED
        self.completed_at = now
        self.updated_at = now
        self.message = "Cancelled"

    def mark_merging(self, now: datetime) -> None:
        self.phase = JobPhase.MERGING
        self.progress_percent = max(self.progress_percent, 95)
        self.updated_at = now
        self.message = "Merging WAV chunks"

    def mark_finalizing(self, now: datetime) -> None:
        self.phase = JobPhase.FINALIZING
        self.progress_percent = max(self.progress_percent, 98)
        self.updated_at = now
        self.message = "Finalizing audio"

    def mark_completed(self, now: datetime) -> None:
        self.status = JobStatus.COMPLETED
        self.phase = JobPhase.COMPLETED
        self.progress_percent = 100
        self.completed_at = now
        self.updated_at = now
        self.message = "Completed"

    def mark_failed(self, reason: str, now: datetime) -> None:
        self.status = JobStatus.FAILED
        self.failure_reason = reason
        self.message = reason
        self.completed_at = now
        self.updated_at = now

    def mark_interrupted(self, message: str, now: datetime) -> None:
        self.status = JobStatus.INTERRUPTED
        self.message = message
        self.completed_at = now
        self.updated_at = now


@dataclass(frozen=True)
class AudioChunk:
    chunk_index: int
    path: str
    duration_seconds: float
    format: str = "wav"


@dataclass(frozen=True)
class FinalAudio:
    project_id: str
    path: str
    duration_seconds: float
    size_bytes: int
    format: str = "wav"


@dataclass(frozen=True)
class QueueSummary:
    pending_count: int
    running_count: int
    completed_count: int
    max_active_jobs_total: int
    concurrency_limits: dict[str, int] = field(default_factory=dict)
    queue_positions: dict[str, int] = field(default_factory=dict)
