from fastapi import APIRouter, Request, status

from study_podcast.adapters.inbound.api.schemas import (
    JobResponse,
    ScriptResponse,
    StartJobRequest,
)
from study_podcast.application.generation_job_commands import (
    RerunGenerationJob,
    SubmitGenerationJob,
)

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
    result = SubmitGenerationJob(
        scripts=container.scripts,
        snapshots=container.snapshots,
        jobs=container.jobs,
        queue=container.queue,
        clock=container.clock,
        max_chunk_chars=container.settings.max_chunk_chars,
        max_chunks=container.settings.max_chunks,
        worker_pool=container.worker_pool,
        auto_start_worker_pool=container.settings.auto_start_worker_pool,
    ).execute(
        project_id,
        voice_profile_id=payload.voice_profile_id,
        tts_params=payload.tts_params,
    )
    return JobResponse.from_domain(result.job, result.snapshot)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(
    request: Request,
    status: str | None = None,
    project_id: str | None = None,
    q: str | None = None,
) -> list[JobResponse]:
    container = request.app.state.container
    statuses = set(status.split(",")) if status else None
    jobs = container.jobs.list()
    if statuses is not None:
        jobs = [job for job in jobs if job.status.value in statuses]
    if project_id is not None:
        jobs = [job for job in jobs if job.project_id == project_id]
    if q:
        query = q.casefold()

        def matches_query(job_id: str) -> bool:
            job = container.jobs.get(job_id)
            if job is None:
                return False
            snapshot = container.snapshots.get(job.id)
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

        jobs = [job for job in jobs if matches_query(job.id)]
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
    result = RerunGenerationJob(
        snapshots=container.snapshots,
        jobs=container.jobs,
        queue=container.queue,
        clock=container.clock,
        worker_pool=container.worker_pool,
        auto_start_worker_pool=container.settings.auto_start_worker_pool,
    ).execute(
        job_id,
    )
    return JobResponse.from_domain(result.job, result.snapshot)


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
