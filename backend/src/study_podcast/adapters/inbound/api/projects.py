from fastapi import APIRouter, Request, status

from study_podcast.adapters.inbound.api.schemas import (
    CreateProjectRequest,
    JobResponse,
    ProjectDetailResponse,
    ProjectResponse,
)
from study_podcast.application.read_models import ProjectReadModel
from study_podcast.application.use_cases import CreateProject

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: CreateProjectRequest, request: Request) -> ProjectResponse:
    container = request.app.state.container
    project = CreateProject(container.projects, container.clock).execute(title=payload.title)
    return ProjectResponse.from_domain(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(request: Request, q: str | None = None) -> list[ProjectResponse]:
    container = request.app.state.container
    projects = ProjectReadModel(container.projects, container.scripts, container.jobs).list(q=q)
    return [ProjectResponse.from_domain(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(project_id: str, request: Request) -> ProjectDetailResponse:
    container = request.app.state.container
    detail = ProjectReadModel(container.projects, container.scripts, container.jobs).get_detail(
        project_id
    )
    return ProjectDetailResponse(
        **ProjectResponse.from_domain(detail.project).model_dump(),
        has_active_script=detail.has_active_script,
        latest_jobs=[JobResponse.from_domain(job) for job in detail.latest_jobs],
    )
