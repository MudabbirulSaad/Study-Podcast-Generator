from fastapi import APIRouter, Request, status

from study_podcast.adapters.inbound.api.schemas import CreateProjectRequest, ProjectResponse
from study_podcast.application.use_cases import CreateProject

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: CreateProjectRequest, request: Request) -> ProjectResponse:
    container = request.app.state.container
    project = CreateProject(container.projects, container.clock).execute(title=payload.title)
    return ProjectResponse.from_domain(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(request: Request) -> list[ProjectResponse]:
    return [
        ProjectResponse.from_domain(project)
        for project in request.app.state.container.projects.list()
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, request: Request) -> ProjectResponse:
    project = request.app.state.container.projects.get(project_id)
    if project is None:
        raise KeyError("project not found")
    return ProjectResponse.from_domain(project)
