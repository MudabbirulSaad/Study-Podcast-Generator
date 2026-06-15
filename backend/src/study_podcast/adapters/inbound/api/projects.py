from fastapi import APIRouter, Request, status

from study_podcast.adapters.inbound.api.schemas import (
    BAD_REQUEST_RESPONSE,
    NOT_FOUND_RESPONSE,
    CreateProjectRequest,
    JobResponse,
    ProjectDetailResponse,
    ProjectResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: BAD_REQUEST_RESPONSE},
    operation_id="projects_create",
)
def create_project(payload: CreateProjectRequest, request: Request) -> ProjectResponse:
    project = request.app.state.container.project_workspace.create_project(payload.title)
    return ProjectResponse.from_domain(project)


@router.get("", response_model=list[ProjectResponse], operation_id="projects_list")
def list_projects(request: Request, q: str | None = None) -> list[ProjectResponse]:
    projects = request.app.state.container.project_workspace.list_projects(q=q)
    return [ProjectResponse.from_domain(project) for project in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    responses={404: NOT_FOUND_RESPONSE},
    operation_id="projects_get",
)
def get_project(project_id: str, request: Request) -> ProjectDetailResponse:
    detail = request.app.state.container.project_workspace.get_project_detail(project_id)
    return ProjectDetailResponse(
        **ProjectResponse.from_domain(detail.project).model_dump(),
        has_active_script=detail.has_active_script,
        latest_jobs=[JobResponse.from_domain(job) for job in detail.latest_jobs],
    )
