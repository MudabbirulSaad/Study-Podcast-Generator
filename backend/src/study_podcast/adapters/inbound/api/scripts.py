from fastapi import APIRouter, Request
from starlette.datastructures import UploadFile

from study_podcast.adapters.inbound.api.schemas import (
    BAD_REQUEST_RESPONSE,
    NOT_FOUND_RESPONSE,
    SaveScriptRequest,
    ScriptResponse,
)
from study_podcast.domain.errors import DomainError
from study_podcast.domain.value_objects import ScriptSource

router = APIRouter(prefix="/projects/{project_id}/script", tags=["scripts"])

SAVE_SCRIPT_REQUEST_BODY = {
    "content": {
        "application/json": {"schema": {"$ref": "#/components/schemas/SaveScriptRequest"}},
        "multipart/form-data": {
            "schema": {
                "type": "object",
                "required": ["file"],
                "properties": {
                    "file": {
                        "type": "string",
                        "format": "binary",
                    }
                },
            }
        },
    },
    "required": True,
}


@router.put(
    "",
    response_model=ScriptResponse,
    responses={400: BAD_REQUEST_RESPONSE},
    openapi_extra={"requestBody": SAVE_SCRIPT_REQUEST_BODY},
    operation_id="scripts_save",
)
async def save_script(project_id: str, request: Request) -> ScriptResponse:
    payload = await _script_payload_from_request(request)
    script, chunks = request.app.state.container.script_endpoint.save_script(
        project_id=project_id,
        text=payload.text,
        source=ScriptSource(payload.source),
    )
    return ScriptResponse.from_domain(script, chunks)


@router.get(
    "",
    response_model=ScriptResponse,
    responses={404: NOT_FOUND_RESPONSE},
    operation_id="scripts_get",
)
def get_script(project_id: str, request: Request) -> ScriptResponse:
    script, chunks = request.app.state.container.script_endpoint.get_script(project_id)
    return ScriptResponse.from_domain(script, chunks)


async def _script_payload_from_request(request: Request) -> SaveScriptRequest:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        return await _script_payload_from_upload(request)
    return SaveScriptRequest.model_validate(await request.json())


async def _script_payload_from_upload(request: Request) -> SaveScriptRequest:
    script_endpoint = request.app.state.container.script_endpoint
    form = await request.form()
    uploaded = form.get("file")
    if not isinstance(uploaded, UploadFile):
        raise DomainError("file is required")
    if not uploaded.filename or not uploaded.filename.lower().endswith(".txt"):
        raise DomainError("uploaded script must be a .txt file")
    if uploaded.content_type not in {"text/plain", "application/octet-stream"}:
        raise DomainError("uploaded script must be plain text")

    content = await uploaded.read(script_endpoint.max_script_size_bytes + 1)
    if len(content) > script_endpoint.max_script_size_bytes:
        raise DomainError("uploaded script is too large")
    return SaveScriptRequest(text=content.decode("utf-8"), source="uploaded")
