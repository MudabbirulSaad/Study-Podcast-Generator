from fastapi import APIRouter, Request, status

from study_podcast.adapters.inbound.api.schemas import JobResponse

router = APIRouter(tags=["jobs"])


@router.post(
    "/projects/{project_id}/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_job(project_id: str, request: Request) -> JobResponse:
    job = request.app.state.container.queue.submit_generation_job(project_id)
    return JobResponse.from_domain(job)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(request: Request) -> list[JobResponse]:
    return [JobResponse.from_domain(job) for job in request.app.state.container.jobs.list()]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, request: Request) -> JobResponse:
    job = request.app.state.container.jobs.get(job_id)
    if job is None:
        raise KeyError("job not found")
    return JobResponse.from_domain(job)


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: str, request: Request) -> JobResponse:
    job = request.app.state.container.queue.cancel(job_id)
    return JobResponse.from_domain(job)
