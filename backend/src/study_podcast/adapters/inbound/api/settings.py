from fastapi import APIRouter, Request, status

from study_podcast.adapters.inbound.api.schemas import (
    BAD_REQUEST_RESPONSE,
    RuntimeSettingsResponse,
    RuntimeStatusResponse,
    TtsEngineSettingsResponse,
    UpdateRuntimeSettingsRequest,
    UpdateTtsEngineRequest,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=RuntimeSettingsResponse, operation_id="settings_get")
def get_runtime_settings(request: Request) -> RuntimeSettingsResponse:
    container = request.app.state.container
    settings_route = container.runtime_settings_endpoint
    return RuntimeSettingsResponse(
        values=settings_route.values(),
        editable_fields=settings_route.editable_fields(),
        available_engines=settings_route.available_engines(),
        reload_required=container.reload_required,
        runtime_status=container.runtime_status,
        last_reload_error=container.last_reload_error,
    )


@router.put(
    "",
    response_model=RuntimeSettingsResponse,
    responses={400: BAD_REQUEST_RESPONSE},
    operation_id="settings_update",
)
def update_runtime_settings(
    payload: UpdateRuntimeSettingsRequest,
    request: Request,
) -> RuntimeSettingsResponse:
    request.app.state.container.runtime_settings_endpoint.update(payload.values)
    return get_runtime_settings(request)


@router.post(
    "/reload",
    response_model=RuntimeStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={400: BAD_REQUEST_RESPONSE},
    operation_id="settings_reload",
)
def reload_runtime_settings(request: Request) -> RuntimeStatusResponse:
    request.app.state.container.runtime_settings_endpoint.reload()
    return get_runtime_status(request)


@router.get(
    "/runtime-status",
    response_model=RuntimeStatusResponse,
    operation_id="settings_runtime_status",
)
def get_runtime_status(request: Request) -> RuntimeStatusResponse:
    container = request.app.state.container
    settings_route = container.runtime_settings_endpoint
    return RuntimeStatusResponse(
        status=container.runtime_status,
        active_engine=settings_route.active_engine(),
        reload_required=container.reload_required,
        last_reload_error=container.last_reload_error,
    )


@router.get(
    "/tts-engines",
    response_model=TtsEngineSettingsResponse,
    operation_id="settings_get_tts_engines",
)
def get_tts_engines(request: Request) -> TtsEngineSettingsResponse:
    container = request.app.state.container
    settings_route = container.runtime_settings_endpoint
    return TtsEngineSettingsResponse(
        active_engine=str(settings_route.values()["active_tts_engine"]),
        available_engines=settings_route.available_engines(),
    )


@router.put(
    "/tts-engine",
    response_model=TtsEngineSettingsResponse,
    responses={400: BAD_REQUEST_RESPONSE},
    operation_id="settings_update_tts_engine",
)
def update_tts_engine(
    payload: UpdateTtsEngineRequest,
    request: Request,
) -> TtsEngineSettingsResponse:
    update_runtime_settings(
        UpdateRuntimeSettingsRequest(values={"active_tts_engine": payload.engine}),
        request,
    )
    return get_tts_engines(request)
