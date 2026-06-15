from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi import Path as PathParam
from fastapi.responses import FileResponse

from study_podcast.adapters.inbound.api.schemas import error_example, error_response

router = APIRouter(tags=["audio"])

PROJECT_ID_PARAM = PathParam(
    description="App-generated project UUID string.",
    json_schema_extra={"format": "uuid"},
)
JOB_ID_PARAM = PathParam(
    description="App-generated job UUID string.",
    json_schema_extra={"format": "uuid"},
)
RANGE_HEADER = Header(
    alias="Range",
    description="Optional byte range request header, for example bytes=0-1023.",
    examples=["bytes=0-1023"],
)
AUDIO_NOT_FOUND_RESPONSE = error_response(
    "Not Found",
    {
        "final_audio_not_found": error_example(
            summary="Final WAV audio is not available",
            code="not_found",
            message="final audio not found",
        )
    },
)

AUDIO_WAV_RESPONSE = {
    "description": "WAV audio file",
    "headers": {
        "Accept-Ranges": {
            "description": "Range unit accepted by the file response.",
            "schema": {"type": "string"},
        },
        "Content-Length": {
            "description": "Size of the response body in bytes.",
            "schema": {"type": "integer"},
        },
    },
    "content": {
        "audio/wav": {
            "schema": {
                "type": "string",
                "format": "binary",
            }
        }
    },
}
AUDIO_PARTIAL_RESPONSE = {
    "description": "Partial WAV audio content",
    "headers": {
        "Accept-Ranges": {
            "description": "Range unit accepted by the file response.",
            "schema": {"type": "string"},
        },
        "Content-Range": {
            "description": "Byte range returned for the partial response.",
            "schema": {"type": "string"},
        },
        "Content-Length": {
            "description": "Size of the partial response body in bytes.",
            "schema": {"type": "integer"},
        },
    },
    "content": {
        "audio/wav": {
            "schema": {
                "type": "string",
                "format": "binary",
            }
        }
    },
}
AUDIO_RANGE_NOT_SATISFIABLE_RESPONSE = {
    "description": "Range Not Satisfiable",
    "headers": {
        "Content-Range": {
            "description": "Unsatisfied byte range and complete resource size.",
            "schema": {"type": "string"},
        }
    },
}
AUDIO_BAD_RANGE_RESPONSE = {
    "description": "Malformed Range header",
    "content": {
        "text/plain": {
            "schema": {
                "type": "string",
                "examples": ["Only support bytes range"],
            }
        }
    },
}
AUDIO_RESPONSES = {
    200: AUDIO_WAV_RESPONSE,
    206: AUDIO_PARTIAL_RESPONSE,
    400: AUDIO_BAD_RANGE_RESPONSE,
    416: AUDIO_RANGE_NOT_SATISFIABLE_RESPONSE,
    404: AUDIO_NOT_FOUND_RESPONSE,
}


@router.get(
    "/projects/{project_id}/audio/final",
    response_class=FileResponse,
    responses=AUDIO_RESPONSES,
    description=(
        "Download the latest completed WAV for the project. This serves the same bytes as "
        "the stream endpoint, but includes a stable download filename."
    ),
    operation_id="audio_download_project_final",
)
def download_final_audio(
    project_id: Annotated[str, PROJECT_ID_PARAM],
    request: Request,
    range_header: Annotated[str | None, RANGE_HEADER] = None,
) -> FileResponse:
    path = _latest_final_audio_path(project_id, request)
    return _audio_response(path, filename="study-podcast.wav")


@router.get(
    "/projects/{project_id}/audio/stream",
    response_class=FileResponse,
    responses=AUDIO_RESPONSES,
    description=(
        "Stream the latest completed WAV for the project. This serves the same bytes as "
        "the final endpoint without a download filename and supports byte-range requests."
    ),
    operation_id="audio_stream_project_final",
)
def stream_final_audio(
    project_id: Annotated[str, PROJECT_ID_PARAM],
    request: Request,
    range_header: Annotated[str | None, RANGE_HEADER] = None,
) -> FileResponse:
    return _audio_response(_latest_final_audio_path(project_id, request))


@router.get(
    "/jobs/{job_id}/audio/final",
    response_class=FileResponse,
    responses=AUDIO_RESPONSES,
    description=(
        "Download the completed WAV for this exact job. This serves the same bytes as "
        "the job stream endpoint, but includes a job-specific download filename."
    ),
    operation_id="audio_download_job_final",
)
def download_job_audio(
    job_id: Annotated[str, JOB_ID_PARAM],
    request: Request,
    range_header: Annotated[str | None, RANGE_HEADER] = None,
) -> FileResponse:
    return _audio_response(
        _job_final_audio_path(job_id, request),
        filename=f"{job_id}.wav",
    )


@router.get(
    "/jobs/{job_id}/audio/stream",
    response_class=FileResponse,
    responses=AUDIO_RESPONSES,
    description=(
        "Stream the completed WAV for this exact job. This serves the same bytes as "
        "the job final endpoint without a download filename and supports byte-range requests."
    ),
    operation_id="audio_stream_job_final",
)
def stream_job_audio(
    job_id: Annotated[str, JOB_ID_PARAM],
    request: Request,
    range_header: Annotated[str | None, RANGE_HEADER] = None,
) -> FileResponse:
    return _audio_response(_job_final_audio_path(job_id, request))


def _audio_response(path: Path, filename: str | None = None) -> FileResponse:
    return FileResponse(
        path,
        media_type="audio/wav",
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )


def _latest_final_audio_path(project_id: str, request: Request) -> Path:
    return request.app.state.container.audio_endpoint.latest_final_audio_path(project_id)


def _job_final_audio_path(job_id: str, request: Request) -> Path:
    return request.app.state.container.audio_endpoint.job_final_audio_path(job_id)
