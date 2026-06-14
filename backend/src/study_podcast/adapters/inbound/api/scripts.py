from fastapi import APIRouter, Request
from starlette.datastructures import UploadFile

from study_podcast.adapters.inbound.api.schemas import SaveScriptRequest, ScriptResponse
from study_podcast.application.use_cases import GetScript, PreviewChunks, SaveActiveScript
from study_podcast.domain.errors import DomainError
from study_podcast.domain.value_objects import ScriptSource

router = APIRouter(prefix="/projects/{project_id}/script", tags=["scripts"])


@router.put("", response_model=ScriptResponse)
async def save_script(project_id: str, request: Request) -> ScriptResponse:
    container = request.app.state.container
    payload = await _script_payload_from_request(request)
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


async def _script_payload_from_request(request: Request) -> SaveScriptRequest:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        return await _script_payload_from_upload(request)
    return SaveScriptRequest.model_validate(await request.json())


async def _script_payload_from_upload(request: Request) -> SaveScriptRequest:
    container = request.app.state.container
    form = await request.form()
    uploaded = form.get("file")
    if not isinstance(uploaded, UploadFile):
        raise DomainError("file is required")
    if not uploaded.filename or not uploaded.filename.lower().endswith(".txt"):
        raise DomainError("uploaded script must be a .txt file")
    if uploaded.content_type not in {"text/plain", "application/octet-stream"}:
        raise DomainError("uploaded script must be plain text")

    content = await uploaded.read(container.settings.max_script_size_bytes + 1)
    if len(content) > container.settings.max_script_size_bytes:
        raise DomainError("uploaded script is too large")
    return SaveScriptRequest(text=content.decode("utf-8"), source="uploaded")
