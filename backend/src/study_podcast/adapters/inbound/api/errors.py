from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from study_podcast.domain.errors import ActiveJobExistsError, DomainError


def error_envelope(
    *,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    return {"code": code, "message": message, "details": details}


def register_error_handlers(app: FastAPI) -> None:
    async def active_job_exists_handler(
        _: Request,
        exc: ActiveJobExistsError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=error_envelope(
                code="active_job_exists",
                message="This project already has an active generation job.",
                details={"job_id": exc.job_id},
            ),
        )

    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=error_envelope(code="domain_error", message=str(exc)),
        )

    async def not_found_handler(_: Request, exc: KeyError) -> JSONResponse:
        message = str(exc).strip("'")
        return JSONResponse(
            status_code=404,
            content=error_envelope(code="not_found", message=message),
        )

    app.add_exception_handler(ActiveJobExistsError, active_job_exists_handler)
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(KeyError, not_found_handler)
