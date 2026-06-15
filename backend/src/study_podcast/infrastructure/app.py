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
        _add_global_metadata(schema)
        save_script_schema = SaveScriptRequest.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        save_script_schema.pop("$defs", None)
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        schemas["SaveScriptRequest"] = save_script_schema
        schemas.pop("Body_voices_upload", None)
        schema["paths"]["/api/v1/projects/{project_id}/jobs"]["post"]["requestBody"] = (
            jobs.START_JOB_REQUEST_BODY
        )
        schema["paths"]["/api/v1/voices"]["post"]["requestBody"] = voices.VOICE_UPLOAD_REQUEST_BODY
        _mark_job_snapshot_required(schema)
        _complete_error_examples(schema)
        _add_success_examples(schema)
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi


def _add_global_metadata(schema: dict) -> None:
    schema["servers"] = [{"url": "/", "description": "Current host"}]
    schema["tags"] = [
        {"name": "projects", "description": "Project workspace metadata and summaries."},
        {"name": "scripts", "description": "Active study script save and retrieval."},
        {"name": "jobs", "description": "Generation job submission, inspection, and control."},
        {"name": "queue", "description": "Generation queue summary."},
        {"name": "audio", "description": "Generated WAV audio downloads and streams."},
        {"name": "settings", "description": "Runtime settings and engine reload controls."},
        {"name": "voices", "description": "Voice profiles and uploaded voice samples."},
    ]


def _mark_job_snapshot_required(schema: dict) -> None:
    job_response = schema.get("components", {}).get("schemas", {}).get("JobResponse")
    if not isinstance(job_response, dict):
        return
    required = job_response.setdefault("required", [])
    if "snapshot" not in required:
        required.append("snapshot")


def _complete_error_examples(schema: dict) -> None:
    for path_item in schema.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            for response in operation.get("responses", {}).values():
                examples = (
                    response.get("content", {}).get("application/json", {}).get("examples", {})
                )
                if not isinstance(examples, dict):
                    continue
                for example in examples.values():
                    value = example.get("value") if isinstance(example, dict) else None
                    if isinstance(value, dict) and value.get("code") in {
                        "domain_error",
                        "not_found",
                    }:
                        value.setdefault("details", None)


def _add_success_examples(schema: dict) -> None:
    _set_json_example(
        schema,
        path="/api/v1/projects",
        method="post",
        status_code="201",
        name="created_project",
        summary="Created project",
        value={
            "id": "00000000-0000-0000-0000-000000000001",
            "title": "Biology 101",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    )
    _set_json_example(
        schema,
        path="/api/v1/projects/{project_id}/script",
        method="put",
        status_code="200",
        name="saved_script",
        summary="Saved script",
        value={
            "project_id": "00000000-0000-0000-0000-000000000001",
            "text": "[Narrator] Cells divide.",
            "source": "pasted",
            "speakers": ["Narrator"],
            "updated_at": "2026-01-01T00:01:00Z",
            "chunks": [
                {
                    "index": 0,
                    "speaker": "Narrator",
                    "text": "Cells divide.",
                }
            ],
        },
    )
    queued_job = {
        "id": "00000000-0000-0000-0000-000000000010",
        "project_id": "00000000-0000-0000-0000-000000000001",
        "status": "queued",
        "phase": "queued",
        "progress_percent": 0,
        "total_chunks": 0,
        "completed_chunks": 0,
        "current_chunk_index": None,
        "current_chunk_preview": None,
        "message": "queued",
        "failure_reason": None,
        "cancellation_requested": False,
        "created_at": "2026-01-01T00:02:00Z",
        "started_at": None,
        "updated_at": "2026-01-01T00:02:00Z",
        "completed_at": None,
        "snapshot": {
            "job_id": "00000000-0000-0000-0000-000000000010",
            "project_id": "00000000-0000-0000-0000-000000000001",
            "script_text": "[Narrator] Cells divide.",
            "script_source": "pasted",
            "speakers": ["Narrator"],
            "chunks": [{"index": 0, "speaker": "Narrator", "text": "Cells divide."}],
            "voice_profile_id": "default",
            "tts_params": {"temperature": 0.4},
            "created_at": "2026-01-01T00:02:00Z",
        },
    }
    _set_json_example(
        schema,
        path="/api/v1/projects/{project_id}/jobs",
        method="post",
        status_code="202",
        name="submitted_job",
        summary="Submitted job",
        value=queued_job,
    )
    completed_job = queued_job | {
        "status": "completed",
        "phase": "completed",
        "progress_percent": 100,
        "total_chunks": 1,
        "completed_chunks": 1,
        "message": "completed",
        "started_at": "2026-01-01T00:02:05Z",
        "updated_at": "2026-01-01T00:02:30Z",
        "completed_at": "2026-01-01T00:02:30Z",
    }
    _set_json_example(
        schema,
        path="/api/v1/jobs/{job_id}",
        method="get",
        status_code="200",
        name="completed_job",
        summary="Completed job",
        value=completed_job,
    )
    _set_json_example(
        schema,
        path="/api/v1/settings",
        method="get",
        status_code="200",
        name="runtime_settings",
        summary="Runtime settings",
        value={
            "values": {
                "active_tts_engine": "chatterbox",
                "chatterbox_device": "auto",
                "max_script_size_bytes": 1000000,
                "max_chunk_chars": 600,
                "max_chunks": 1000,
                "chatterbox_max_concurrent_jobs": 1,
                "audio_merge_max_concurrent_jobs": 1,
                "max_active_jobs_total": 10,
                "storage_root": "data/storage",
                "frontend_origin": "http://localhost:5173",
                "serve_frontend": True,
            },
            "editable_fields": [
                "active_tts_engine",
                "chatterbox_device",
                "max_script_size_bytes",
                "max_chunk_chars",
                "max_chunks",
                "chatterbox_max_concurrent_jobs",
                "audio_merge_max_concurrent_jobs",
                "max_active_jobs_total",
                "storage_root",
                "frontend_origin",
                "serve_frontend",
            ],
            "available_engines": ["chatterbox"],
            "reload_required": False,
            "runtime_status": "idle",
            "last_reload_error": None,
        },
    )
    _set_json_example(
        schema,
        path="/api/v1/voices",
        method="post",
        status_code="201",
        name="uploaded_voice",
        summary="Uploaded voice profile",
        value={
            "id": "00000000-0000-0000-0000-000000000020",
            "display_name": "Seminar voice",
            "source": "uploaded",
            "sample_path": "data/storage/voices/00000000-0000-0000-0000-000000000020/sample.wav",
            "has_sample": True,
            "created_at": "2026-01-01T00:03:00Z",
            "updated_at": "2026-01-01T00:03:00Z",
        },
    )


def _set_json_example(
    schema: dict,
    *,
    path: str,
    method: str,
    status_code: str,
    name: str,
    summary: str,
    value: dict,
) -> None:
    media_type = (
        schema["paths"][path][method]["responses"][status_code]
        .setdefault("content", {})
        .setdefault("application/json", {})
    )
    media_type.setdefault("examples", {})[name] = {"summary": summary, "value": value}


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
