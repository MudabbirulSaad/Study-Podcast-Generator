from fastapi import APIRouter, Request, status

from study_podcast.adapters.inbound.api.schemas import (
    JobResponse,
    ScriptResponse,
    StartJobRequest,
)
from study_podcast.domain.entities import JobInputSnapshot
from study_podcast.domain.errors import DomainError
from study_podcast.domain.services import split_script_into_chunks

router = APIRouter(tags=["jobs"])


@router.post(
    "/projects/{project_id}/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_job(
    project_id: str,
    request: Request,
    payload: StartJobRequest | None = None,
) -> JobResponse:
    container = request.app.state.container
    payload = payload or StartJobRequest()
    script = container.scripts.get_active(project_id)
    if script is None:
        raise DomainError("script not found")
    chunks = split_script_into_chunks(
        script.text,
        max_chunk_chars=container.settings.max_chunk_chars,
        max_chunks=container.settings.max_chunks,
    )
    job = container.queue.submit_generation_job(project_id)
    snapshot = JobInputSnapshot(
        job_id=job.id,
        project_id=project_id,
        script_text=script.text,
        script_source=script.source,
        speakers=script.speakers,
        chunks=tuple(chunks),
        voice_profile_id=payload.voice_profile_id,
        tts_params=payload.tts_params,
        created_at=container.clock.now(),
    )
    container.snapshots.save(snapshot)
    if container.settings.auto_start_worker_pool:
        container.worker_pool.drain_queued()
        job = container.jobs.get(job.id) or job
    return JobResponse.from_domain(job, snapshot)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(
    request: Request,
    status: str | None = None,
    project_id: str | None = None,
) -> list[JobResponse]:
    container = request.app.state.container
    statuses = set(status.split(",")) if status else None
    jobs = container.jobs.list()
    if statuses is not None:
        jobs = [job for job in jobs if job.status.value in statuses]
    if project_id is not None:
        jobs = [job for job in jobs if job.project_id == project_id]
    return [JobResponse.from_domain(job, container.snapshots.get(job.id)) for job in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, request: Request) -> JobResponse:
    job = request.app.state.container.jobs.get(job_id)
    if job is None:
        raise KeyError("job not found")
    snapshot = request.app.state.container.snapshots.get(job_id)
    return JobResponse.from_domain(job, snapshot)


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: str, request: Request) -> JobResponse:
    job = request.app.state.container.queue.cancel(job_id)
    snapshot = request.app.state.container.snapshots.get(job_id)
    return JobResponse.from_domain(job, snapshot)


@router.post(
    "/jobs/{job_id}/rerun",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def rerun_job(job_id: str, request: Request) -> JobResponse:
    container = request.app.state.container
    existing_snapshot = container.snapshots.get(job_id)
    if existing_snapshot is None:
        raise KeyError("job snapshot not found")
    job = container.queue.submit_generation_job(existing_snapshot.project_id)
    snapshot = JobInputSnapshot(
        job_id=job.id,
        project_id=existing_snapshot.project_id,
        script_text=existing_snapshot.script_text,
        script_source=existing_snapshot.script_source,
        speakers=existing_snapshot.speakers,
        chunks=existing_snapshot.chunks,
        voice_profile_id=existing_snapshot.voice_profile_id,
        tts_params=existing_snapshot.tts_params,
        created_at=container.clock.now(),
    )
    container.snapshots.save(snapshot)
    if container.settings.auto_start_worker_pool:
        container.worker_pool.drain_queued()
        job = container.jobs.get(job.id) or job
    return JobResponse.from_domain(job, snapshot)


@router.get("/jobs/{job_id}/script", response_model=ScriptResponse)
def get_job_script(job_id: str, request: Request) -> ScriptResponse:
    container = request.app.state.container
    snapshot = container.snapshots.get(job_id)
    if snapshot is None:
        raise KeyError("job snapshot not found")
    return ScriptResponse(
        project_id=snapshot.project_id,
        text=snapshot.script_text,
        source=snapshot.script_source.value,
        speakers=list(snapshot.speakers),
        updated_at=snapshot.created_at,
        chunks=[],
    )
