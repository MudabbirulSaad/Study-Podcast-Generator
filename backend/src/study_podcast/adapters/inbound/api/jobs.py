from fastapi import APIRouter, Request, status

from study_podcast.adapters.inbound.api.schemas import (
    JobResponse,
    ScriptResponse,
    StartJobRequest,
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
    payload = payload or StartJobRequest()
    result = request.app.state.container.generation_jobs.submit(
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
    results = request.app.state.container.generation_jobs.list(
        status=status,
        project_id=project_id,
        q=q,
    )
    return [JobResponse.from_domain(result.job, result.snapshot) for result in results]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, request: Request) -> JobResponse:
    result = request.app.state.container.generation_jobs.get(job_id)
    return JobResponse.from_domain(result.job, result.snapshot)


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: str, request: Request) -> JobResponse:
    result = request.app.state.container.generation_jobs.cancel(job_id)
    return JobResponse.from_domain(result.job, result.snapshot)


@router.post(
    "/jobs/{job_id}/rerun",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def rerun_job(job_id: str, request: Request) -> JobResponse:
    result = request.app.state.container.generation_jobs.rerun(job_id)
    return JobResponse.from_domain(result.job, result.snapshot)


@router.get("/jobs/{job_id}/script", response_model=ScriptResponse)
def get_job_script(job_id: str, request: Request) -> ScriptResponse:
    snapshot = request.app.state.container.generation_jobs.get_script_snapshot(job_id)
    return ScriptResponse(
        project_id=snapshot.project_id,
        text=snapshot.script_text,
        source=snapshot.script_source.value,
        speakers=list(snapshot.speakers),
        updated_at=snapshot.created_at,
        chunks=[],
    )
