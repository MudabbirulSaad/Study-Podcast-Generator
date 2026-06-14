from fastapi import APIRouter, Request

from study_podcast.adapters.inbound.api.schemas import (
    TtsEngineSettingsResponse,
    UpdateTtsEngineRequest,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/tts-engines", response_model=TtsEngineSettingsResponse)
def get_tts_engines(request: Request) -> TtsEngineSettingsResponse:
    settings = request.app.state.container.settings
    return TtsEngineSettingsResponse(
        active_engine=settings.active_tts_engine,
        available_engines=["fake", "chatterbox"],
    )


@router.put("/tts-engine", response_model=TtsEngineSettingsResponse)
def update_tts_engine(
    payload: UpdateTtsEngineRequest,
    request: Request,
) -> TtsEngineSettingsResponse:
    if payload.engine not in {"fake", "chatterbox"}:
        raise KeyError("tts engine not found")
    request.app.state.container.settings.active_tts_engine = payload.engine
    return get_tts_engines(request)
