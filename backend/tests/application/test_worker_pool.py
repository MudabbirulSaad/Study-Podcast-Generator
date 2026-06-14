from concurrent.futures import Future
from datetime import UTC, datetime
from threading import Lock
from time import sleep

from study_podcast.adapters.outbound.in_memory_repositories import InMemoryJobRepository
from study_podcast.adapters.outbound.in_process_worker_pool import InProcessWorkerPool
from study_podcast.domain.entities import GenerationJob
from study_podcast.domain.value_objects import JobStatus


class RecordingRunner:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.lock = Lock()

    def run(self, job_id: str):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        sleep(0.03)
        with self.lock:
            self.active -= 1
        return job_id


def seed_jobs(jobs: InMemoryJobRepository, count: int) -> None:
    now = datetime(2026, 6, 14, tzinfo=UTC)
    for index in range(count):
        jobs.save(GenerationJob.create(f"project-{index}", now))


def test_fake_engine_can_run_multiple_jobs_when_configured() -> None:
    jobs = InMemoryJobRepository()
    seed_jobs(jobs, 4)
    runner = RecordingRunner()
    pool = InProcessWorkerPool(
        jobs=jobs,
        runner=runner,
        engine_key="fake",
        concurrency_limits={"fake": 4},
    )

    futures = pool.drain_queued()
    for future in futures:
        future.result(timeout=1)

    assert runner.max_active > 1


def test_chatterbox_engine_runs_one_job_by_default() -> None:
    jobs = InMemoryJobRepository()
    seed_jobs(jobs, 3)
    runner = RecordingRunner()
    pool = InProcessWorkerPool(
        jobs=jobs,
        runner=runner,
        engine_key="chatterbox",
        concurrency_limits={"chatterbox": 1},
    )

    futures: list[Future] = pool.drain_queued()
    for future in futures:
        future.result(timeout=1)

    assert runner.max_active == 1


def test_cancelled_queued_job_never_starts() -> None:
    jobs = InMemoryJobRepository()
    now = datetime(2026, 6, 14, tzinfo=UTC)
    cancelled = GenerationJob.create("project-1", now)
    cancelled.mark_cancelled(now)
    jobs.save(cancelled)
    runner = RecordingRunner()

    futures = InProcessWorkerPool(
        jobs=jobs,
        runner=runner,
        engine_key="fake",
        concurrency_limits={"fake": 4},
    ).drain_queued()

    assert futures == []
    assert cancelled.status is JobStatus.CANCELLED
