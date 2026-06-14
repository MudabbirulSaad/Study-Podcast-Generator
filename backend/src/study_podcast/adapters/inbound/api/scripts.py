from fastapi import APIRouter, Request

from study_podcast.adapters.inbound.api.schemas import SaveScriptRequest, ScriptResponse
from study_podcast.application.use_cases import GetScript, PreviewChunks, SaveActiveScript
from study_podcast.domain.value_objects import ScriptSource

router = APIRouter(prefix="/projects/{project_id}/script", tags=["scripts"])


@router.put("", response_model=ScriptResponse)
def save_script(project_id: str, payload: SaveScriptRequest, request: Request) -> ScriptResponse:
    container = request.app.state.container
    script = SaveActiveScript(container.projects, container.scripts, container.clock).execute(
        project_id=project_id,
        text=payload.text,
        source=ScriptSource(payload.source),
    )
    chunks = PreviewChunks(
        container.scripts,
        max_chunk_chars=container.settings.max_chunk_chars,
        max_chunks=container.settings.max_chunks,
    ).execute(project_id)
    return ScriptResponse.from_domain(script, chunks)


@router.get("", response_model=ScriptResponse)
def get_script(project_id: str, request: Request) -> ScriptResponse:
    container = request.app.state.container
    script = GetScript(container.scripts).execute(project_id)
    if script is None:
        raise KeyError("script not found")
    chunks = PreviewChunks(
        container.scripts,
        max_chunk_chars=container.settings.max_chunk_chars,
        max_chunks=container.settings.max_chunks,
    ).execute(project_id)
    return ScriptResponse.from_domain(script, chunks)
