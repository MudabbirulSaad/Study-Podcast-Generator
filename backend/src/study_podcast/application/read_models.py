from dataclasses import dataclass
from typing import Any

from study_podcast.domain.entities import GenerationJob, JobInputSnapshot, StudyProject
from study_podcast.domain.ports import (
    FileStorage,
    JobInputSnapshotRepository,
    JobRepository,
    ProjectRepository,
    ScriptRepository,
)


@dataclass(frozen=True)
class ProjectDetail:
    project: StudyProject
    has_active_script: bool
    latest_jobs: list[GenerationJob]


@dataclass(frozen=True)
class JobResult:
    job: GenerationJob
    snapshot: JobInputSnapshot | None


@dataclass(frozen=True)
class ProjectReadModel:
    projects: ProjectRepository
    scripts: ScriptRepository
    jobs: JobRepository

    def list(self, q: str | None = None) -> list[StudyProject]:
        projects = self.projects.list()
        if not q:
            return projects
        query = q.casefold()
        return [project for project in projects if query in project.title.casefold()]

    def get_detail(self, project_id: str) -> ProjectDetail:
        project = self.projects.get(project_id)
        if project is None:
            raise KeyError("project not found")
        latest_jobs = [job for job in self.jobs.list() if job.project_id == project_id][-5:]
        latest_jobs.reverse()
        return ProjectDetail(
            project=project,
            has_active_script=self.scripts.get_active(project_id) is not None,
            latest_jobs=latest_jobs,
        )


@dataclass(frozen=True)
class JobReadModel:
    jobs: JobRepository
    snapshots: JobInputSnapshotRepository

    def list(
        self,
        *,
        status: str | None = None,
        project_id: str | None = None,
        q: str | None = None,
    ) -> list[JobResult]:
        statuses = set(status.split(",")) if status else None
        jobs = self.jobs.list()
        if statuses is not None:
            jobs = [job for job in jobs if job.status.value in statuses]
        if project_id is not None:
            jobs = [job for job in jobs if job.project_id == project_id]
        if q:
            query = q.casefold()
            jobs = [job for job in jobs if self._matches_query(job, query)]
        return [JobResult(job=job, snapshot=self.snapshots.get(job.id)) for job in jobs]

    def get(self, job_id: str) -> JobResult:
        job = self.jobs.get(job_id)
        if job is None:
            raise KeyError("job not found")
        return JobResult(job=job, snapshot=self.snapshots.get(job_id))

    def get_script_snapshot(self, job_id: str) -> JobInputSnapshot:
        snapshot = self.snapshots.get(job_id)
        if snapshot is None:
            raise KeyError("job snapshot not found")
        return snapshot

    def _matches_query(self, job: GenerationJob, query: str) -> bool:
        snapshot = self.snapshots.get(job.id)
        searchable = [
            job.id,
            job.project_id,
            job.status.value,
            job.phase.value,
            job.message,
            job.failure_reason or "",
            snapshot.script_text if snapshot is not None else "",
        ]
        return any(query in value.casefold() for value in searchable)


@dataclass(frozen=True)
class AudioReadModel:
    jobs: JobRepository
    storage: FileStorage

    def latest_final_audio_path(self, project_id: str) -> Any:
        completed_jobs = [
            job
            for job in self.jobs.list()
            if job.project_id == project_id and job.status.value == "completed"
        ]
        if not completed_jobs:
            raise KeyError("final audio not found")
        latest = completed_jobs[-1]
        path = self.storage.path_for_final_audio(project_id, latest.id)
        if not path.exists():
            raise KeyError("final audio not found")
        return path

    def job_final_audio_path(self, job_id: str) -> Any:
        job = self.jobs.get(job_id)
        if job is None or job.status.value != "completed":
            raise KeyError("final audio not found")
        path = self.storage.path_for_final_audio(job.project_id, job.id)
        if not path.exists():
            raise KeyError("final audio not found")
        return path
