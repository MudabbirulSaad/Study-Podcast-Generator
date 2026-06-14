from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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
from study_podcast.domain.errors import ActiveJobExistsError, DomainError
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

    @app.exception_handler(ActiveJobExistsError)
    def active_job_exists_handler(_: Request, exc: ActiveJobExistsError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "code": "active_job_exists",
                "message": "This project already has an active generation job.",
                "details": {"job_id": exc.job_id},
            },
        )

    @app.exception_handler(DomainError)
    def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"code": "domain_error", "message": str(exc), "details": None},
        )

    @app.exception_handler(KeyError)
    def not_found_handler(_: Request, exc: KeyError) -> JSONResponse:
        message = str(exc).strip("'")
        return JSONResponse(
            status_code=404,
            content={"code": "not_found", "message": message, "details": None},
        )

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
    _configure_frontend_static(app, container.settings)
    return app


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
