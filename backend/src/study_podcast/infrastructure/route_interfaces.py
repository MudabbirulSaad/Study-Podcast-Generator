from dataclasses import dataclass
from pathlib import Path

from study_podcast.application.generation_job_commands import (
    GenerationJobCommandResult,
    RerunGenerationJob,
    SubmitGenerationJob,
)
from study_podcast.application.read_models import (
    AudioReadModel,
    JobReadModel,
    JobResult,
    ProjectDetail,
    ProjectReadModel,
)
from study_podcast.application.use_cases import (
    CreateProject,
    GetScript,
    PreviewChunks,
    SaveActiveScript,
)
from study_podcast.domain.entities import (
    ActivePodcastScript,
    StudyProject,
    TextChunk,
    VoiceProfile,
)
from study_podcast.domain.errors import DomainError
from study_podcast.domain.value_objects import ScriptSource
from study_podcast.infrastructure.runtime_settings import (
    EDITABLE_SETTINGS,
    available_engines,
    settings_snapshot,
)
from study_podcast.infrastructure.runtime_settings_transaction import RuntimeSettingsTransaction


@dataclass(frozen=True)
class ProjectWorkspaceRoutes:
    container: object

    def create_project(self, title: str) -> StudyProject:
        return CreateProject(self.container.projects, self.container.clock).execute(title=title)

    def list_projects(self, q: str | None = None) -> list[StudyProject]:
        return ProjectReadModel(
            self.container.projects,
            self.container.scripts,
            self.container.jobs,
        ).list(q=q)

    def get_project_detail(self, project_id: str) -> ProjectDetail:
        return ProjectReadModel(
            self.container.projects,
            self.container.scripts,
            self.container.jobs,
        ).get_detail(project_id)


@dataclass(frozen=True)
class ScriptRoutes:
    container: object

    @property
    def max_script_size_bytes(self) -> int:
        return self.container.settings.max_script_size_bytes

    def save_script(
        self,
        *,
        project_id: str,
        text: str,
        source: ScriptSource,
    ) -> tuple[ActivePodcastScript, list[TextChunk]]:
        script = SaveActiveScript(
            self.container.projects,
            self.container.scripts,
            self.container.clock,
        ).execute(project_id=project_id, text=text, source=source)
        return script, self._preview_chunks(project_id)

    def get_script(self, project_id: str) -> tuple[ActivePodcastScript, list[TextChunk]]:
        script = GetScript(self.container.scripts).execute(project_id)
        if script is None:
            raise KeyError("script not found")
        return script, self._preview_chunks(project_id)

    def _preview_chunks(self, project_id: str) -> list[TextChunk]:
        return PreviewChunks(
            self.container.scripts,
            max_chunk_chars=self.container.settings.max_chunk_chars,
            max_chunks=self.container.settings.max_chunks,
        ).execute(project_id)


@dataclass(frozen=True)
class GenerationJobRoutes:
    container: object

    def submit(
        self,
        project_id: str,
        *,
        voice_profile_id: str,
        tts_params: dict[str, float],
    ) -> GenerationJobCommandResult:
        return SubmitGenerationJob(
            scripts=self.container.scripts,
            snapshots=self.container.snapshots,
            jobs=self.container.jobs,
            queue=self.container.queue,
            clock=self.container.clock,
            max_chunk_chars=self.container.settings.max_chunk_chars,
            max_chunks=self.container.settings.max_chunks,
            worker_pool=self.container.worker_pool,
            auto_start_worker_pool=self.container.settings.auto_start_worker_pool,
        ).execute(
            project_id,
            voice_profile_id=voice_profile_id,
            tts_params=tts_params,
        )

    def list(
        self,
        *,
        status: str | None = None,
        project_id: str | None = None,
        q: str | None = None,
    ) -> list[JobResult]:
        return JobReadModel(self.container.jobs, self.container.snapshots).list(
            status=status,
            project_id=project_id,
            q=q,
        )

    def get(self, job_id: str) -> JobResult:
        return JobReadModel(self.container.jobs, self.container.snapshots).get(job_id)

    def cancel(self, job_id: str) -> JobResult:
        job = self.container.queue.cancel(job_id)
        return JobResult(job=job, snapshot=self.container.snapshots.get(job_id))

    def rerun(self, job_id: str) -> GenerationJobCommandResult:
        return RerunGenerationJob(
            snapshots=self.container.snapshots,
            jobs=self.container.jobs,
            queue=self.container.queue,
            clock=self.container.clock,
            worker_pool=self.container.worker_pool,
            auto_start_worker_pool=self.container.settings.auto_start_worker_pool,
        ).execute(job_id)

    def get_script_snapshot(self, job_id: str):
        return JobReadModel(
            self.container.jobs,
            self.container.snapshots,
        ).get_script_snapshot(job_id)


@dataclass(frozen=True)
class QueueRoutes:
    container: object

    def summary(self):
        return self.container.queue.summary()


@dataclass(frozen=True)
class AudioRoutes:
    container: object

    def latest_final_audio_path(self, project_id: str) -> Path:
        return AudioReadModel(self.container.jobs, self.container.storage).latest_final_audio_path(
            project_id
        )

    def job_final_audio_path(self, job_id: str) -> Path:
        return AudioReadModel(
            self.container.jobs,
            self.container.storage,
        ).job_final_audio_path(job_id)


@dataclass(frozen=True)
class RuntimeSettingsRoutes:
    container: object

    def values(self) -> dict[str, object]:
        return settings_snapshot(self.container.settings)

    def editable_fields(self) -> list[str]:
        return list(EDITABLE_SETTINGS)

    def available_engines(self) -> list[str]:
        return available_engines(self.container.settings)

    def update(self, values: dict[str, object]) -> None:
        RuntimeSettingsTransaction(self.container).update(values)

    def reload(self) -> None:
        RuntimeSettingsTransaction(self.container).reload()

    def active_engine(self) -> str:
        return self.container.worker_pool.engine_key


@dataclass(frozen=True)
class VoiceRoutes:
    container: object

    def list(self) -> list[VoiceProfile]:
        return self.container.voices.list()

    def upload(self, *, display_name: str, filename: str | None, content: bytes) -> VoiceProfile:
        clean_name = display_name.strip()
        if not clean_name:
            raise DomainError("voice display name is required")
        extension = Path(filename or "").suffix.lower()
        if extension not in {".wav", ".mp3", ".flac", ".m4a"}:
            raise DomainError("voice sample must be wav, mp3, flac, or m4a")

        now = self.container.clock.now()
        profile = VoiceProfile.uploaded(
            display_name=clean_name,
            sample_path="pending",
            now=now,
        )
        target = self.container.storage.path_for_voice_sample(profile.id, extension)
        self.container.storage.write_bytes_atomic(target, content)
        saved = VoiceProfile(
            id=profile.id,
            display_name=profile.display_name,
            source=profile.source,
            sample_path=str(target),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
        self.container.voices.save(saved)
        return saved
