from dataclasses import dataclass
from datetime import UTC, datetime

from study_podcast.adapters.outbound.audio_merger_wav import WavAudioMerger
from study_podcast.adapters.outbound.filesystem import LocalFileStorage
from study_podcast.adapters.outbound.in_process_worker_pool import InProcessWorkerPool
from study_podcast.adapters.outbound.persistence_sqlite import (
    SQLiteJobRepository,
    SQLiteProjectRepository,
    SQLiteScriptRepository,
    SQLiteStore,
)
from study_podcast.adapters.outbound.tts_chatterbox import ChatterboxTtsEngine
from study_podcast.adapters.outbound.tts_fake import FakeTtsEngine
from study_podcast.application.job_queue import DefaultJobQueue
from study_podcast.application.job_runner import GenerationJobRunner
from study_podcast.application.progress import RepositoryProgressReporter
from study_podcast.infrastructure.config import Settings


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass
class Container:
    settings: Settings
    clock: SystemClock
    projects: SQLiteProjectRepository
    scripts: SQLiteScriptRepository
    jobs: SQLiteJobRepository
    queue: DefaultJobQueue
    storage: LocalFileStorage
    runner: GenerationJobRunner
    worker_pool: InProcessWorkerPool

    @classmethod
    def create(cls, settings: Settings | None = None) -> "Container":
        resolved_settings = settings or Settings()
        clock = SystemClock()
        store = SQLiteStore(resolved_settings.database_path)
        jobs = SQLiteJobRepository(store)
        scripts = SQLiteScriptRepository(store)
        storage = LocalFileStorage(resolved_settings.storage_root)
        tts = (
            ChatterboxTtsEngine()
            if resolved_settings.active_tts_engine == "chatterbox"
            else FakeTtsEngine()
        )
        runner = GenerationJobRunner(
            scripts=scripts,
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
            projects=SQLiteProjectRepository(store),
            scripts=scripts,
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
