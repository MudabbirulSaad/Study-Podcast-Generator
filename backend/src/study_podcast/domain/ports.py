from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from study_podcast.domain.entities import (
    ActivePodcastScript,
    AudioChunk,
    FinalAudio,
    GenerationJob,
    JobInputSnapshot,
    QueueSummary,
    StudyProject,
    TextChunk,
)


class ProjectRepository(Protocol):
    def save(self, project: StudyProject) -> None: ...
    def get(self, project_id: str) -> StudyProject | None: ...
    def list(self) -> list[StudyProject]: ...


class ScriptRepository(Protocol):
    def save_active(self, script: ActivePodcastScript) -> None: ...
    def get_active(self, project_id: str) -> ActivePodcastScript | None: ...


class JobRepository(Protocol):
    def save(self, job: GenerationJob) -> None: ...
    def get(self, job_id: str) -> GenerationJob | None: ...
    def list(self) -> list[GenerationJob]: ...
    def find_active_for_project(self, project_id: str) -> GenerationJob | None: ...
    def list_unfinished(self) -> list[GenerationJob]: ...


class JobInputSnapshotRepository(Protocol):
    def save(self, snapshot: JobInputSnapshot) -> None: ...
    def get(self, job_id: str) -> JobInputSnapshot | None: ...


class TtsEngine(Protocol):
    engine_key: str

    def synthesize(
        self,
        *,
        chunk: TextChunk,
        output_path: Any,
        voice_prompt_path: Any | None = None,
        tts_params: dict[str, float] | None = None,
    ) -> AudioChunk: ...


class AudioMerger(Protocol):
    def merge(self, *, chunks: Iterable[AudioChunk], output_path: Any) -> FinalAudio: ...


class FileStorage(Protocol):
    def path_for_chunk(self, project_id: str, job_id: str, chunk_index: int) -> Any: ...
    def path_for_final_audio(self, project_id: str, job_id: str) -> Any: ...


class JobQueue(Protocol):
    def submit_generation_job(self, project_id: str) -> GenerationJob: ...
    def cancel(self, job_id: str) -> GenerationJob: ...
    def summary(self) -> QueueSummary: ...


class ProgressReporter(Protocol):
    def save(self, job: GenerationJob) -> None: ...


class SettingsRepository(Protocol):
    def save_many(self, values: dict[str, str]) -> None: ...
    def list(self) -> dict[str, str]: ...


class EnvFileWriter(Protocol):
    def write(self, values: dict[str, object]) -> None: ...


class RuntimeEngineReloader(Protocol):
    def reload(self) -> None: ...
