from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

router = APIRouter(prefix="/projects/{project_id}/audio", tags=["audio"])


@router.get("/final")
def download_final_audio(project_id: str, request: Request) -> FileResponse:
    path = _latest_final_audio_path(project_id, request)
    return _audio_response(path, filename="study-podcast.wav")


@router.get("/stream")
def stream_final_audio(project_id: str, request: Request) -> FileResponse:
    return _audio_response(_latest_final_audio_path(project_id, request))


def _audio_response(path: Path, filename: str | None = None) -> FileResponse:
    return FileResponse(
        path,
        media_type="audio/wav",
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )


def _latest_final_audio_path(project_id: str, request: Request) -> Path:
    container = request.app.state.container
    completed_jobs = [
        job
        for job in container.jobs.list()
        if job.project_id == project_id and job.status == "completed"
    ]
    if not completed_jobs:
        raise KeyError("final audio not found")
    latest = completed_jobs[-1]
    path = container.storage.path_for_final_audio(project_id, latest.id)
    if not path.exists():
        raise KeyError("final audio not found")
    return path
