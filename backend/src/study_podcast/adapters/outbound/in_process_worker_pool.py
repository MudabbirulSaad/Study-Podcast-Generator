from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field

from study_podcast.domain.ports import JobRepository
from study_podcast.domain.value_objects import JobStatus


@dataclass
class InProcessWorkerPool:
    jobs: JobRepository
    runner: object
    engine_key: str
    concurrency_limits: dict[str, int]
    _executors: dict[str, ThreadPoolExecutor] = field(default_factory=dict)

    def drain_queued(self) -> list[Future]:
        queued_jobs = [job for job in self.jobs.list() if job.status is JobStatus.QUEUED]
        if not queued_jobs:
            return []

        max_workers = max(1, self.concurrency_limits.get(self.engine_key, 1))
        executor = self._executors.get(self.engine_key)
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tts-job")
            self._executors[self.engine_key] = executor
        return [executor.submit(self.runner.run, job.id) for job in queued_jobs]

    def shutdown(self) -> None:
        for executor in self._executors.values():
            executor.shutdown(wait=True)
        self._executors.clear()
