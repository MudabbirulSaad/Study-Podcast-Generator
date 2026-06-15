from typing import Annotated

from fastapi import APIRouter, Path, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from study_podcast.adapters.inbound.api.schemas import (
    SaveScriptRequest,
    ScriptResponse,
    error_example,
    error_response,
)
from study_podcast.domain.errors import DomainError
from study_podcast.domain.value_objects import ScriptSource

router = APIRouter(prefix="/projects/{project_id}/script", tags=["scripts"])

PROJECT_ID_PARAM = Path(
    description="App-generated project UUID string.",
    json_schema_extra={"format": "uuid"},
)
SAVE_SCRIPT_BAD_REQUEST_RESPONSE = error_response(
    "Bad Request",
    {
        "script_text_required": error_example(
            summary="Script text is empty",
            code="domain_error",
            message="script text is required",
        ),
        "project_not_found": error_example(
            summary="Project was not found",
            code="domain_error",
            message="project not found",
        ),
        "uploaded_script_not_text": error_example(
            summary="Uploaded script is not plain text",
            code="domain_error",
            message="uploaded script must be plain text",
        ),
        "uploaded_script_too_large": error_example(
            summary="Uploaded script exceeds configured limit",
            code="domain_error",
            message="uploaded script is too large",
        ),
    },
)
SCRIPT_NOT_FOUND_RESPONSE = error_response(
    "Not Found",
    {
        "script_not_found": error_example(
            summary="Project has no active script",
            code="not_found",
            message="script not found",
        )
    },
)

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
                        "description": (
                            "Plain text script upload. Runtime accepts .txt files with "
                            "content type text/plain or application/octet-stream. The file "
                            "is read as UTF-8 and rejected when it exceeds the configured "
                            "max_script_size_bytes setting."
                        ),
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
    responses={400: SAVE_SCRIPT_BAD_REQUEST_RESPONSE},
    openapi_extra={"requestBody": SAVE_SCRIPT_REQUEST_BODY},
    operation_id="scripts_save",
)
async def save_script(
    project_id: Annotated[str, PROJECT_ID_PARAM], request: Request
) -> ScriptResponse:
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
    responses={404: SCRIPT_NOT_FOUND_RESPONSE},
    operation_id="scripts_get",
)
def get_script(project_id: Annotated[str, PROJECT_ID_PARAM], request: Request) -> ScriptResponse:
    script, chunks = request.app.state.container.script_endpoint.get_script(project_id)
    return ScriptResponse.from_domain(script, chunks)


async def _script_payload_from_request(request: Request) -> SaveScriptRequest:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        return await _script_payload_from_upload(request)
    try:
        return SaveScriptRequest.model_validate(await request.json())
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


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
