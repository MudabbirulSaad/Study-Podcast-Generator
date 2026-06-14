from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

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
    completed_jobs = [
        job
        for job in container.jobs.list()
        if job.project_id == project_id and job.status.value == "completed"
    ]
    if not completed_jobs:
        raise KeyError("final audio not found")
    latest = completed_jobs[-1]
    path = container.storage.path_for_final_audio(project_id, latest.id)
    if not path.exists():
        raise KeyError("final audio not found")
    return path


def _job_final_audio_path(job_id: str, request: Request) -> Path:
    container = request.app.state.container
    job = container.jobs.get(job_id)
    if job is None or job.status.value != "completed":
        raise KeyError("final audio not found")
    path = container.storage.path_for_final_audio(job.project_id, job.id)
    if not path.exists():
        raise KeyError("final audio not found")
    return path
