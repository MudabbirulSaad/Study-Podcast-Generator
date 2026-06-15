from datetime import UTC, datetime

from study_podcast.adapters.outbound.in_memory_repositories import (
    InMemoryJobInputSnapshotRepository,
    InMemoryJobRepository,
    InMemoryScriptRepository,
)
from study_podcast.application.generation_job_commands import SubmitGenerationJob
from study_podcast.application.job_queue import DefaultJobQueue
from study_podcast.domain.entities import ActivePodcastScript
from study_podcast.domain.value_objects import ScriptSource


class FixedClock:
    def now(self):
        return datetime(2026, 6, 15, tzinfo=UTC)


class WorkerKick:
    def __init__(self) -> None:
        self.drain_count = 0

    def drain_queued(self) -> None:
        self.drain_count += 1


def test_submit_generation_job_creates_snapshot_and_kicks_worker() -> None:
    clock = FixedClock()
    scripts = InMemoryScriptRepository()
    jobs = InMemoryJobRepository()
    snapshots = InMemoryJobInputSnapshotRepository()
    worker = WorkerKick()
    scripts.save_active(
        ActivePodcastScript(
            project_id="project-1",
            text="[S1] First sentence. [S2] Second sentence.",
            source=ScriptSource.PASTED,
            speakers=("S1", "S2"),
            updated_at=clock.now(),
        )
    )
    queue = DefaultJobQueue(
        jobs=jobs,
        clock=clock,
        max_active_jobs_total=10,
    )
    command = SubmitGenerationJob(
        scripts=scripts,
        snapshots=snapshots,
        jobs=jobs,
        queue=queue,
        clock=clock,
        max_chunk_chars=24,
        max_chunks=10,
        worker_pool=worker,
        auto_start_worker_pool=True,
    )

    result = command.execute(
        "project-1",
        voice_profile_id="voice-1",
        tts_params={"temperature": 0.4},
    )

    snapshot = snapshots.get(result.job.id)
    assert result.job.status.value == "queued"
    assert snapshot is not None
    assert snapshot.script_text == "[S1] First sentence. [S2] Second sentence."
    assert snapshot.voice_profile_id == "voice-1"
    assert snapshot.tts_params == {"temperature": 0.4}
    assert snapshot.speakers == ("S1", "S2")
    assert len(snapshot.chunks) > 1
    assert worker.drain_count == 1
