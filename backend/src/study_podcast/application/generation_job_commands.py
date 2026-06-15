from dataclasses import dataclass
from typing import Protocol

from study_podcast.application.use_cases import Clock
from study_podcast.domain.entities import GenerationJob, JobInputSnapshot
from study_podcast.domain.errors import DomainError
from study_podcast.domain.ports import (
    JobInputSnapshotRepository,
    JobQueue,
    JobRepository,
    ScriptRepository,
)
from study_podcast.domain.services import split_script_into_chunks


class WorkerPool(Protocol):
    def drain_queued(self): ...


@dataclass(frozen=True)
class GenerationJobCommandResult:
    job: GenerationJob
    snapshot: JobInputSnapshot


@dataclass(frozen=True)
class SubmitGenerationJob:
    scripts: ScriptRepository
    snapshots: JobInputSnapshotRepository
    jobs: JobRepository
    queue: JobQueue
    clock: Clock
    max_chunk_chars: int
    max_chunks: int
    worker_pool: WorkerPool
    auto_start_worker_pool: bool

    def execute(
        self,
        project_id: str,
        *,
        voice_profile_id: str,
        tts_params: dict[str, float],
    ) -> GenerationJobCommandResult:
        script = self.scripts.get_active(project_id)
        if script is None:
            raise DomainError("script not found")
        chunks = split_script_into_chunks(
            script.text,
            max_chunk_chars=self.max_chunk_chars,
            max_chunks=self.max_chunks,
        )
        job = self.queue.submit_generation_job(project_id)
        snapshot = JobInputSnapshot(
            job_id=job.id,
            project_id=project_id,
            script_text=script.text,
            script_source=script.source,
            speakers=script.speakers,
            chunks=tuple(chunks),
            voice_profile_id=voice_profile_id,
            tts_params=tts_params,
            created_at=self.clock.now(),
        )
        self.snapshots.save(snapshot)
        job = self._drain_and_refresh(job)
        return GenerationJobCommandResult(job=job, snapshot=snapshot)

    def _drain_and_refresh(self, job: GenerationJob) -> GenerationJob:
        if not self.auto_start_worker_pool:
            return job
        self.worker_pool.drain_queued()
        return self.jobs.get(job.id) or job


@dataclass(frozen=True)
class RerunGenerationJob:
    snapshots: JobInputSnapshotRepository
    jobs: JobRepository
    queue: JobQueue
    clock: Clock
    worker_pool: WorkerPool
    auto_start_worker_pool: bool

    def execute(self, job_id: str) -> GenerationJobCommandResult:
        existing_snapshot = self.snapshots.get(job_id)
        if existing_snapshot is None:
            raise KeyError("job snapshot not found")
        job = self.queue.submit_generation_job(existing_snapshot.project_id)
        snapshot = JobInputSnapshot(
            job_id=job.id,
            project_id=existing_snapshot.project_id,
            script_text=existing_snapshot.script_text,
            script_source=existing_snapshot.script_source,
            speakers=existing_snapshot.speakers,
            chunks=existing_snapshot.chunks,
            voice_profile_id=existing_snapshot.voice_profile_id,
            tts_params=existing_snapshot.tts_params,
            created_at=self.clock.now(),
        )
        self.snapshots.save(snapshot)
        if self.auto_start_worker_pool:
            self.worker_pool.drain_queued()
            job = self.jobs.get(job.id) or job
        return GenerationJobCommandResult(job=job, snapshot=snapshot)
