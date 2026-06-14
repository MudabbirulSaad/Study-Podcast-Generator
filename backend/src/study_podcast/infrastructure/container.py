from dataclasses import dataclass
from datetime import UTC, datetime

from study_podcast.adapters.outbound.in_memory_repositories import (
    InMemoryJobRepository,
    InMemoryProjectRepository,
    InMemoryScriptRepository,
)
from study_podcast.application.job_queue import DefaultJobQueue
from study_podcast.infrastructure.config import Settings


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass
class Container:
    settings: Settings
    clock: SystemClock
    projects: InMemoryProjectRepository
    scripts: InMemoryScriptRepository
    jobs: InMemoryJobRepository
    queue: DefaultJobQueue

    @classmethod
    def create(cls, settings: Settings | None = None) -> "Container":
        resolved_settings = settings or Settings()
        clock = SystemClock()
        jobs = InMemoryJobRepository()
        return cls(
            settings=resolved_settings,
            clock=clock,
            projects=InMemoryProjectRepository(),
            scripts=InMemoryScriptRepository(),
            jobs=jobs,
            queue=DefaultJobQueue(
                jobs=jobs,
                clock=clock,
                max_active_jobs_total=resolved_settings.max_active_jobs_total,
                concurrency_limits=resolved_settings.concurrency_limits,
            ),
        )
