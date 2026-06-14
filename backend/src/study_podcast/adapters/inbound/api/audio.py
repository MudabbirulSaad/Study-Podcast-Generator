from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/audio", tags=["audio"])


@router.get("/final")
def download_final_audio(project_id: str) -> dict[str, str]:
    return {"project_id": project_id, "message": "final audio not generated yet"}


@router.get("/stream")
def stream_final_audio(project_id: str) -> dict[str, str]:
    return {"project_id": project_id, "message": "final audio not generated yet"}
