from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile, status

from study_podcast.adapters.inbound.api.schemas import VoiceProfileResponse
from study_podcast.domain.entities import VoiceProfile
from study_podcast.domain.errors import DomainError

router = APIRouter(prefix="/voices", tags=["voices"])

SUPPORTED_VOICE_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a"}


@router.get("", response_model=list[VoiceProfileResponse])
def list_voices(request: Request) -> list[VoiceProfileResponse]:
    return [
        VoiceProfileResponse.from_domain(profile)
        for profile in request.app.state.container.voices.list()
    ]


@router.post("", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def upload_voice(
    request: Request,
    display_name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> VoiceProfileResponse:
    clean_name = display_name.strip()
    if not clean_name:
        raise DomainError("voice display name is required")
    extension = Path(file.filename or "").suffix.lower()
    if extension not in SUPPORTED_VOICE_EXTENSIONS:
        raise DomainError("voice sample must be wav, mp3, flac, or m4a")

    container = request.app.state.container
    now = container.clock.now()
    profile = VoiceProfile.uploaded(
        display_name=clean_name,
        sample_path="pending",
        now=now,
    )
    target = container.storage.path_for_voice_sample(profile.id, extension)
    content = await file.read()
    container.storage.write_bytes_atomic(target, content)
    saved = VoiceProfile(
        id=profile.id,
        display_name=profile.display_name,
        source=profile.source,
        sample_path=str(target),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
    container.voices.save(saved)
    return VoiceProfileResponse.from_domain(saved)
