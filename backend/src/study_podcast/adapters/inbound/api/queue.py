from fastapi import APIRouter, Request

from study_podcast.adapters.inbound.api.schemas import QueueResponse

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=QueueResponse)
def queue_summary(request: Request) -> QueueResponse:
    return QueueResponse.from_domain(request.app.state.container.queue.summary())
