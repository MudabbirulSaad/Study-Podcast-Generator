from fastapi import APIRouter, Request, status

from study_podcast.adapters.inbound.api.schemas import (
    CreateProjectRequest,
    JobResponse,
    ProjectDetailResponse,
    ProjectResponse,
)
from study_podcast.application.use_cases import CreateProject

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: CreateProjectRequest, request: Request) -> ProjectResponse:
    container = request.app.state.container
    project = CreateProject(container.projects, container.clock).execute(title=payload.title)
    return ProjectResponse.from_domain(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(request: Request, q: str | None = None) -> list[ProjectResponse]:
    projects = request.app.state.container.projects.list()
    if q:
        query = q.casefold()
        projects = [project for project in projects if query in project.title.casefold()]
    return [ProjectResponse.from_domain(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(project_id: str, request: Request) -> ProjectDetailResponse:
    container = request.app.state.container
    project = container.projects.get(project_id)
    if project is None:
        raise KeyError("project not found")
    latest_jobs = [job for job in container.jobs.list() if job.project_id == project_id][-5:]
    latest_jobs.reverse()
    return ProjectDetailResponse(
        **ProjectResponse.from_domain(project).model_dump(),
        has_active_script=container.scripts.get_active(project_id) is not None,
        latest_jobs=[JobResponse.from_domain(job) for job in latest_jobs],
    )
