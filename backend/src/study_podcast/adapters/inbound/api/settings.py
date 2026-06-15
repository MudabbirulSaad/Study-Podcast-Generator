from fastapi import APIRouter, Request, status

from study_podcast.adapters.inbound.api.schemas import (
    RuntimeSettingsResponse,
    RuntimeStatusResponse,
    TtsEngineSettingsResponse,
    UpdateRuntimeSettingsRequest,
    UpdateTtsEngineRequest,
)
from study_podcast.infrastructure.runtime_settings import (
    EDITABLE_SETTINGS,
    available_engines,
    settings_snapshot,
)
from study_podcast.infrastructure.runtime_settings_transaction import RuntimeSettingsTransaction

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=RuntimeSettingsResponse)
def get_runtime_settings(request: Request) -> RuntimeSettingsResponse:
    container = request.app.state.container
    return RuntimeSettingsResponse(
        values=settings_snapshot(container.settings),
        editable_fields=list(EDITABLE_SETTINGS),
        available_engines=available_engines(container.settings),
        reload_required=container.reload_required,
        runtime_status=container.runtime_status,
        last_reload_error=container.last_reload_error,
    )


@router.put("", response_model=RuntimeSettingsResponse)
def update_runtime_settings(
    payload: UpdateRuntimeSettingsRequest,
    request: Request,
) -> RuntimeSettingsResponse:
    container = request.app.state.container
    RuntimeSettingsTransaction(container).update(payload.values)
    return get_runtime_settings(request)


@router.post("/reload", response_model=RuntimeStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def reload_runtime_settings(request: Request) -> RuntimeStatusResponse:
    container = request.app.state.container
    RuntimeSettingsTransaction(container).reload()
    return get_runtime_status(request)


@router.get("/runtime-status", response_model=RuntimeStatusResponse)
def get_runtime_status(request: Request) -> RuntimeStatusResponse:
    container = request.app.state.container
    return RuntimeStatusResponse(
        status=container.runtime_status,
        active_engine=container.worker_pool.engine_key,
        reload_required=container.reload_required,
        last_reload_error=container.last_reload_error,
    )


@router.get("/tts-engines", response_model=TtsEngineSettingsResponse)
def get_tts_engines(request: Request) -> TtsEngineSettingsResponse:
    container = request.app.state.container
    return TtsEngineSettingsResponse(
        active_engine=container.settings.active_tts_engine,
        available_engines=available_engines(container.settings),
    )


@router.put("/tts-engine", response_model=TtsEngineSettingsResponse)
def update_tts_engine(
    payload: UpdateTtsEngineRequest,
    request: Request,
) -> TtsEngineSettingsResponse:
    update_runtime_settings(
        UpdateRuntimeSettingsRequest(values={"active_tts_engine": payload.engine}),
        request,
    )
    return get_tts_engines(request)
