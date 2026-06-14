from datetime import UTC, datetime

from study_podcast.adapters.outbound.in_memory_repositories import InMemoryJobRepository
from study_podcast.domain.entities import GenerationJob
from study_podcast.domain.value_objects import JobStatus
from study_podcast.infrastructure.startup_recovery import mark_unfinished_jobs_interrupted


class FixedClock:
    def now(self):
        return datetime(2026, 6, 14, tzinfo=UTC)


def test_startup_recovery_marks_unfinished_jobs_interrupted() -> None:
    jobs = InMemoryJobRepository()
    queued = GenerationJob.create("project-1", FixedClock().now())
    completed = GenerationJob.create("project-2", FixedClock().now())
    completed.mark_completed(FixedClock().now())
    jobs.save(queued)
    jobs.save(completed)

    mark_unfinished_jobs_interrupted(jobs, FixedClock())

    assert jobs.get(queued.id).status is JobStatus.INTERRUPTED
    assert jobs.get(queued.id).message == "Server restarted before this job completed."
    assert jobs.get(completed.id).status is JobStatus.COMPLETED
