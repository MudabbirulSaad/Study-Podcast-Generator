from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from study_podcast.application.read_models import AudioReadModel

router = APIRouter(tags=["audio"])


@router.get("/projects/{project_id}/audio/final")
def download_final_audio(project_id: str, request: Request) -> FileResponse:
    path = _latest_final_audio_path(project_id, request)
    return _audio_response(path, filename="study-podcast.wav")


@router.get("/projects/{project_id}/audio/stream")
def stream_final_audio(project_id: str, request: Request) -> FileResponse:
    return _audio_response(_latest_final_audio_path(project_id, request))


@router.get("/jobs/{job_id}/audio/final")
def download_job_audio(job_id: str, request: Request) -> FileResponse:
    return _audio_response(
        _job_final_audio_path(job_id, request),
        filename=f"{job_id}.wav",
    )


@router.get("/jobs/{job_id}/audio/stream")
def stream_job_audio(job_id: str, request: Request) -> FileResponse:
    return _audio_response(_job_final_audio_path(job_id, request))


def _audio_response(path: Path, filename: str | None = None) -> FileResponse:
    return FileResponse(
        path,
        media_type="audio/wav",
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )


def _latest_final_audio_path(project_id: str, request: Request) -> Path:
    container = request.app.state.container
    return AudioReadModel(container.jobs, container.storage).latest_final_audio_path(project_id)


def _job_final_audio_path(job_id: str, request: Request) -> Path:
    container = request.app.state.container
    return AudioReadModel(container.jobs, container.storage).job_final_audio_path(job_id)
