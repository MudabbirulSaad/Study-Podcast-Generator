from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile, status

from study_podcast.adapters.inbound.api.schemas import BAD_REQUEST_RESPONSE, VoiceProfileResponse

router = APIRouter(prefix="/voices", tags=["voices"])

VOICE_UPLOAD_REQUEST_BODY = {
    "content": {
        "multipart/form-data": {
            "schema": {
                "type": "object",
                "required": ["display_name", "file"],
                "properties": {
                    "display_name": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Non-empty display name after trimming whitespace.",
                    },
                    "file": {
                        "type": "string",
                        "format": "binary",
                        "description": (
                            "Voice sample upload. Runtime accepts filenames ending in .wav, "
                            ".mp3, .flac, or .m4a. MIME type is not validated and no upload "
                            "size limit is currently enforced here."
                        ),
                    },
                },
            }
        }
    },
    "required": True,
}


@router.get("", response_model=list[VoiceProfileResponse], operation_id="voices_list")
def list_voices(request: Request) -> list[VoiceProfileResponse]:
    return [
        VoiceProfileResponse.from_domain(profile)
        for profile in request.app.state.container.voice_endpoint.list()
    ]


@router.post(
    "",
    response_model=VoiceProfileResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: BAD_REQUEST_RESPONSE},
    openapi_extra={"requestBody": VOICE_UPLOAD_REQUEST_BODY},
    operation_id="voices_upload",
)
async def upload_voice(
    request: Request,
    display_name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> VoiceProfileResponse:
    saved = request.app.state.container.voice_endpoint.upload(
        display_name=display_name,
        filename=file.filename,
        content=await file.read(),
    )
    return VoiceProfileResponse.from_domain(saved)
