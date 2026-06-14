from study_podcast.application.use_cases import Clock
from study_podcast.domain.ports import JobRepository


def mark_unfinished_jobs_interrupted(jobs: JobRepository, clock: Clock) -> None:
    for job in jobs.list_unfinished():
        job.mark_interrupted("Server restarted before this job completed.", clock.now())
        jobs.save(job)
