from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile, status

from study_podcast.adapters.inbound.api.schemas import VoiceProfileResponse

router = APIRouter(prefix="/voices", tags=["voices"])


@router.get("", response_model=list[VoiceProfileResponse])
def list_voices(request: Request) -> list[VoiceProfileResponse]:
    return [
        VoiceProfileResponse.from_domain(profile)
        for profile in request.app.state.container.voice_endpoint.list()
    ]


@router.post("", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
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
