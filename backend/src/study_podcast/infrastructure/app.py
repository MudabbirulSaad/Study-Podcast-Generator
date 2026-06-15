from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from study_podcast.adapters.inbound.api import (
    audio,
    jobs,
    projects,
    queue,
    scripts,
    settings,
    voices,
)
from study_podcast.adapters.inbound.api.errors import register_error_handlers
from study_podcast.adapters.inbound.api.schemas import SaveScriptRequest
from study_podcast.infrastructure.config import Settings
from study_podcast.infrastructure.container import Container
from study_podcast.infrastructure.startup_recovery import mark_unfinished_jobs_interrupted


def create_app(settings_override: Settings | None = None) -> FastAPI:
    container = Container.create(settings_override)
    mark_unfinished_jobs_interrupted(container.jobs, container.clock)
    app = FastAPI(title="Study Podcast Generator API")
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[container.settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    for router in (
        projects.router,
        scripts.router,
        jobs.router,
        queue.router,
        audio.router,
        settings.router,
        voices.router,
    ):
        app.include_router(router, prefix="/api/v1")
    _configure_openapi(app)
    _configure_frontend_static(app, container.settings)
    return app


def _configure_openapi(app: FastAPI) -> None:
    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        save_script_schema = SaveScriptRequest.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        save_script_schema.pop("$defs", None)
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        schemas["SaveScriptRequest"] = save_script_schema
        schemas.pop("Body_voices_upload", None)
        schema["paths"]["/api/v1/voices"]["post"]["requestBody"] = voices.VOICE_UPLOAD_REQUEST_BODY
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi


def _configure_frontend_static(app: FastAPI, settings: Settings) -> None:
    dist_path = settings.frontend_dist_path
    index_path = dist_path / "index.html"
    if not settings.serve_frontend or not index_path.exists():
        return

    assets_path = dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="frontend-assets")

    @app.get("/")
    def serve_frontend_index() -> FileResponse:
        return FileResponse(index_path)

    @app.get("/{full_path:path}", response_model=None)
    def serve_frontend_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(
                status_code=404,
                content={
                    "code": "not_found",
                    "message": "API route not found",
                    "details": None,
                },
            )
        requested_path = (dist_path / full_path).resolve()
        if requested_path.is_relative_to(dist_path.resolve()) and requested_path.is_file():
            return FileResponse(requested_path)
        return FileResponse(index_path)
