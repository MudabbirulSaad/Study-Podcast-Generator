from dataclasses import dataclass
from datetime import UTC, datetime

from study_podcast.adapters.outbound.audio_merger_wav import WavAudioMerger
from study_podcast.adapters.outbound.filesystem import LocalFileStorage
from study_podcast.adapters.outbound.in_process_worker_pool import InProcessWorkerPool
from study_podcast.adapters.outbound.persistence_sqlite import (
    SQLiteJobInputSnapshotRepository,
    SQLiteJobRepository,
    SQLiteProjectRepository,
    SQLiteScriptRepository,
    SQLiteSettingsRepository,
    SQLiteStore,
    SQLiteVoiceProfileRepository,
)
from study_podcast.adapters.outbound.tts_chatterbox import ChatterboxTtsEngine
from study_podcast.adapters.outbound.tts_fake import FakeTtsEngine
from study_podcast.application.job_queue import DefaultJobQueue
from study_podcast.application.job_runner import GenerationJobRunner
from study_podcast.application.progress import RepositoryProgressReporter
from study_podcast.domain.errors import DomainError
from study_podcast.domain.value_objects import JobStatus
from study_podcast.infrastructure.config import Settings
from study_podcast.infrastructure.route_interfaces import (
    AudioRoutes,
    GenerationJobRoutes,
    ProjectWorkspaceRoutes,
    QueueRoutes,
    RuntimeSettingsRoutes,
    ScriptRoutes,
    VoiceRoutes,
)
from study_podcast.infrastructure.runtime_settings import (
    DotEnvFileWriter,
    apply_startup_overrides,
)


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass
class Container:
    settings: Settings
    clock: SystemClock
    settings_repo: SQLiteSettingsRepository
    env_writer: DotEnvFileWriter
    projects: SQLiteProjectRepository
    scripts: SQLiteScriptRepository
    snapshots: SQLiteJobInputSnapshotRepository
    voices: SQLiteVoiceProfileRepository
    jobs: SQLiteJobRepository
    queue: DefaultJobQueue
    storage: LocalFileStorage
    runner: GenerationJobRunner
    worker_pool: InProcessWorkerPool
    reload_required: bool = False
    runtime_status: str = "idle"
    last_reload_error: str | None = None

    @property
    def project_workspace(self) -> ProjectWorkspaceRoutes:
        return ProjectWorkspaceRoutes(self)

    @property
    def script_endpoint(self) -> ScriptRoutes:
        return ScriptRoutes(self)

    @property
    def generation_jobs(self) -> GenerationJobRoutes:
        return GenerationJobRoutes(self)

    @property
    def generation_queue(self) -> QueueRoutes:
        return QueueRoutes(self)

    @property
    def audio_endpoint(self) -> AudioRoutes:
        return AudioRoutes(self)

    @property
    def runtime_settings_endpoint(self) -> RuntimeSettingsRoutes:
        return RuntimeSettingsRoutes(self)

    @property
    def voice_endpoint(self) -> VoiceRoutes:
        return VoiceRoutes(self)

    @classmethod
    def create(cls, settings: Settings | None = None) -> "Container":
        resolved_settings = settings or Settings()
        clock = SystemClock()
        store = SQLiteStore(resolved_settings.database_path)
        settings_repo = SQLiteSettingsRepository(store)
        apply_startup_overrides(resolved_settings, settings_repo.list())
        jobs = SQLiteJobRepository(store)
        scripts = SQLiteScriptRepository(store)
        snapshots = SQLiteJobInputSnapshotRepository(store)
        voices = SQLiteVoiceProfileRepository(store)
        storage = LocalFileStorage(resolved_settings.storage_root)
        tts = _create_tts_engine(resolved_settings)
        runner = GenerationJobRunner(
            scripts=scripts,
            snapshots=snapshots,
            voices=voices,
            jobs=jobs,
            tts=tts,
            merger=WavAudioMerger(),
            storage=storage,
            progress=RepositoryProgressReporter(jobs),
            clock=clock,
            max_chunk_chars=resolved_settings.max_chunk_chars,
            max_chunks=resolved_settings.max_chunks,
        )
        return cls(
            settings=resolved_settings,
            clock=clock,
            settings_repo=settings_repo,
            env_writer=DotEnvFileWriter(resolved_settings.env_file_path),
            projects=SQLiteProjectRepository(store),
            scripts=scripts,
            snapshots=snapshots,
            voices=voices,
            jobs=jobs,
            queue=DefaultJobQueue(
                jobs=jobs,
                clock=clock,
                max_active_jobs_total=resolved_settings.max_active_jobs_total,
                concurrency_limits=resolved_settings.concurrency_limits,
            ),
            storage=storage,
            runner=runner,
            worker_pool=InProcessWorkerPool(
                jobs=jobs,
                runner=runner,
                engine_key=resolved_settings.active_tts_engine,
                concurrency_limits=resolved_settings.concurrency_limits,
            ),
        )

    def rebuild_runtime(self) -> None:
        active_statuses = {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.CANCEL_REQUESTED}
        if any(job.status in active_statuses for job in self.jobs.list()):
            raise DomainError("runtime reload requires all active jobs to finish or be cancelled")

        self.runtime_status = "reloading"
        previous = (self.queue, self.runner, self.worker_pool, self.runtime_status)
        try:
            tts = _create_tts_engine(self.settings)
            runner = GenerationJobRunner(
                scripts=self.scripts,
                snapshots=self.snapshots,
                voices=self.voices,
                jobs=self.jobs,
                tts=tts,
                merger=WavAudioMerger(),
                storage=self.storage,
                progress=RepositoryProgressReporter(self.jobs),
                clock=self.clock,
                max_chunk_chars=self.settings.max_chunk_chars,
                max_chunks=self.settings.max_chunks,
            )
            worker_pool = InProcessWorkerPool(
                jobs=self.jobs,
                runner=runner,
                engine_key=self.settings.active_tts_engine,
                concurrency_limits=self.settings.concurrency_limits,
            )
        except Exception as exc:
            self.queue, self.runner, self.worker_pool, _ = previous
            self.runtime_status = "failed"
            self.last_reload_error = str(exc)
            raise DomainError(str(exc)) from exc

        self.worker_pool.shutdown()
        self.runner = runner
        self.queue = DefaultJobQueue(
            jobs=self.jobs,
            clock=self.clock,
            max_active_jobs_total=self.settings.max_active_jobs_total,
            concurrency_limits=self.settings.concurrency_limits,
        )
        self.worker_pool = worker_pool
        self.reload_required = False
        self.runtime_status = "ready"
        self.last_reload_error = None


def _create_tts_engine(settings: Settings):
    if settings.active_tts_engine == "chatterbox":
        return ChatterboxTtsEngine(device=settings.chatterbox_device)
    if settings.active_tts_engine == "fake" and settings.enable_dev_tts_engine:
        return FakeTtsEngine()
    if settings.active_tts_engine == "fake":
        raise DomainError("development TTS engine is disabled")
    raise DomainError(f"tts engine not found: {settings.active_tts_engine}")
