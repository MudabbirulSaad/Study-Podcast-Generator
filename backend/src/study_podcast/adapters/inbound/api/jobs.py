from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, status

from study_podcast.adapters.inbound.api.schemas import (
    BAD_REQUEST_RESPONSE,
    CONFLICT_RESPONSE,
    NOT_FOUND_RESPONSE,
    JobResponse,
    ScriptResponse,
    StartJobRequest,
)
from study_podcast.domain.value_objects import JobStatus

router = APIRouter(tags=["jobs"])

PROJECT_ID_PARAM = Path(
    description="App-generated project UUID string.",
    json_schema_extra={"format": "uuid"},
)
JOB_ID_PARAM = Path(
    description="App-generated job UUID string.",
    json_schema_extra={"format": "uuid"},
)
JOB_STATUS_FILTER = Query(
    description="Comma-separated job statuses. Unknown values currently return no matches.",
    examples=["queued,running"],
    json_schema_extra={"x-accepted-values": [status.value for status in JobStatus]},
)
START_JOB_REQUEST_BODY = {
    "content": {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/StartJobRequest"},
        }
    },
    "required": False,
}


@router.post(
    "/projects/{project_id}/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={400: BAD_REQUEST_RESPONSE, 409: CONFLICT_RESPONSE},
    openapi_extra={"requestBody": START_JOB_REQUEST_BODY},
    operation_id="jobs_submit",
)
def submit_job(
    project_id: Annotated[str, PROJECT_ID_PARAM],
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


@router.get("/jobs", response_model=list[JobResponse], operation_id="jobs_list")
def list_jobs(
    request: Request,
    status: Annotated[str | None, JOB_STATUS_FILTER] = None,
    project_id: str | None = None,
    q: str | None = None,
) -> list[JobResponse]:
    results = request.app.state.container.generation_jobs.list(
        status=status,
        project_id=project_id,
        q=q,
    )
    return [JobResponse.from_domain(result.job, result.snapshot) for result in results]


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    responses={404: NOT_FOUND_RESPONSE},
    operation_id="jobs_get",
)
def get_job(job_id: Annotated[str, JOB_ID_PARAM], request: Request) -> JobResponse:
    result = request.app.state.container.generation_jobs.get(job_id)
    return JobResponse.from_domain(result.job, result.snapshot)


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobResponse,
    responses={400: BAD_REQUEST_RESPONSE},
    operation_id="jobs_cancel",
)
def cancel_job(job_id: Annotated[str, JOB_ID_PARAM], request: Request) -> JobResponse:
    result = request.app.state.container.generation_jobs.cancel(job_id)
    return JobResponse.from_domain(result.job, result.snapshot)


@router.post(
    "/jobs/{job_id}/rerun",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: BAD_REQUEST_RESPONSE,
        404: NOT_FOUND_RESPONSE,
        409: CONFLICT_RESPONSE,
    },
    operation_id="jobs_rerun",
)
def rerun_job(job_id: Annotated[str, JOB_ID_PARAM], request: Request) -> JobResponse:
    result = request.app.state.container.generation_jobs.rerun(job_id)
    return JobResponse.from_domain(result.job, result.snapshot)


@router.get(
    "/jobs/{job_id}/script",
    response_model=ScriptResponse,
    responses={404: NOT_FOUND_RESPONSE},
    operation_id="jobs_get_script",
)
def get_job_script(job_id: Annotated[str, JOB_ID_PARAM], request: Request) -> ScriptResponse:
    snapshot = request.app.state.container.generation_jobs.get_script_snapshot(job_id)
    return ScriptResponse(
        project_id=snapshot.project_id,
        text=snapshot.script_text,
        source=snapshot.script_source.value,
        speakers=list(snapshot.speakers),
        updated_at=snapshot.created_at,
        chunks=[],
    )
