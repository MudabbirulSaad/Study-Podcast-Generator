from dataclasses import dataclass

from study_podcast.domain.entities import GenerationJob
from study_podcast.domain.ports import JobRepository


@dataclass(frozen=True)
class RepositoryProgressReporter:
    jobs: JobRepository

    def save(self, job: GenerationJob) -> None:
        self.jobs.save(job)
