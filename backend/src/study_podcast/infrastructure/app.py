from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from study_podcast.adapters.inbound.api import audio, jobs, projects, queue, scripts, settings
from study_podcast.domain.errors import ActiveJobExistsError, DomainError
from study_podcast.infrastructure.config import Settings
from study_podcast.infrastructure.container import Container


def create_app(settings_override: Settings | None = None) -> FastAPI:
    container = Container.create(settings_override)
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
    ):
        app.include_router(router, prefix="/api/v1")
    return app
