from datetime import UTC, datetime

import pytest

from study_podcast.adapters.outbound.in_memory_repositories import InMemoryJobRepository
from study_podcast.application.job_queue import DefaultJobQueue
from study_podcast.domain.errors import ActiveJobExistsError, DomainError
from study_podcast.domain.value_objects import JobStatus


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 6, 14, tzinfo=UTC)


def test_submitting_multiple_jobs_creates_multiple_queued_jobs() -> None:
    jobs = InMemoryJobRepository()
    queue = DefaultJobQueue(jobs=jobs, clock=FixedClock(), max_active_jobs_total=10)

    first = queue.submit_generation_job("project-1")
    second = queue.submit_generation_job("project-2")

    assert first.status is JobStatus.QUEUED
    assert second.status is JobStatus.QUEUED
    assert {job.project_id for job in jobs.list()} == {"project-1", "project-2"}


def test_duplicate_active_job_for_project_is_rejected() -> None:
    jobs = InMemoryJobRepository()
    queue = DefaultJobQueue(jobs=jobs, clock=FixedClock(), max_active_jobs_total=10)
    existing = queue.submit_generation_job("project-1")

    with pytest.raises(ActiveJobExistsError) as error:
        queue.submit_generation_job("project-1")

    assert error.value.job_id == existing.id


def test_queue_rejects_when_total_active_limit_is_reached() -> None:
    queue = DefaultJobQueue(
        jobs=InMemoryJobRepository(),
        clock=FixedClock(),
        max_active_jobs_total=1,
    )
    queue.submit_generation_job("project-1")

    with pytest.raises(DomainError, match="maximum active job limit"):
        queue.submit_generation_job("project-2")


def test_cancelled_queued_job_never_counts_as_active() -> None:
    jobs = InMemoryJobRepository()
    queue = DefaultJobQueue(jobs=jobs, clock=FixedClock(), max_active_jobs_total=10)
    job = queue.submit_generation_job("project-1")

    cancelled = queue.cancel(job.id)
    replacement = queue.submit_generation_job("project-1")

    assert cancelled.status is JobStatus.CANCELLED
    assert replacement.status is JobStatus.QUEUED


def test_queue_summary_reports_counts_and_positions() -> None:
    jobs = InMemoryJobRepository()
    queue = DefaultJobQueue(
        jobs=jobs,
        clock=FixedClock(),
        max_active_jobs_total=10,
        concurrency_limits={"fake": 4, "chatterbox": 1, "merge": 1},
    )
    first = queue.submit_generation_job("project-1")
    second = queue.submit_generation_job("project-2")
    first.mark_running(FixedClock().now())
    jobs.save(first)

    summary = queue.summary()

    assert summary.pending_count == 1
    assert summary.running_count == 1
    assert summary.queue_positions == {second.id: 1}
    assert summary.concurrency_limits["chatterbox"] == 1
