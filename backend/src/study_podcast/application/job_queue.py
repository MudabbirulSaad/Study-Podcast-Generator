from dataclasses import dataclass, field

from study_podcast.application.use_cases import Clock
from study_podcast.domain.entities import GenerationJob, QueueSummary
from study_podcast.domain.errors import ActiveJobExistsError, DomainError
from study_podcast.domain.ports import JobRepository
from study_podcast.domain.value_objects import JobStatus


@dataclass(frozen=True)
class DefaultJobQueue:
    jobs: JobRepository
    clock: Clock
    max_active_jobs_total: int
    concurrency_limits: dict[str, int] = field(default_factory=dict)

    def submit_generation_job(self, project_id: str) -> GenerationJob:
        existing = self.jobs.find_active_for_project(project_id)
        if existing is not None:
            raise ActiveJobExistsError(existing.id)

        active_count = sum(1 for job in self.jobs.list() if job.status.is_active)
        if active_count >= self.max_active_jobs_total:
            raise DomainError("maximum active job limit reached")

        job = GenerationJob.create(project_id=project_id, created_at=self.clock.now())
        self.jobs.save(job)
        return job

    def cancel(self, job_id: str) -> GenerationJob:
        job = self.jobs.get(job_id)
        if job is None:
            raise DomainError("job not found")
        now = self.clock.now()
        if job.status is JobStatus.QUEUED:
            job.request_cancellation(now)
            job.mark_cancelled(now)
        elif job.status is JobStatus.RUNNING:
            job.request_cancellation(now)
        elif job.status is JobStatus.CANCEL_REQUESTED:
            pass
        else:
            raise DomainError("job cannot be cancelled")
        self.jobs.save(job)
        return job

    def summary(self) -> QueueSummary:
        all_jobs = self.jobs.list()
        queued = [job for job in all_jobs if job.status is JobStatus.QUEUED]
        running = [job for job in all_jobs if job.status is JobStatus.RUNNING]
        completed = [
            job
            for job in all_jobs
            if job.status
            in {
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
                JobStatus.INTERRUPTED,
            }
        ]
        return QueueSummary(
            pending_count=len(queued),
            running_count=len(running),
            completed_count=len(completed),
            max_active_jobs_total=self.max_active_jobs_total,
            concurrency_limits=self.concurrency_limits,
            queue_positions={job.id: index + 1 for index, job in enumerate(queued)},
        )
