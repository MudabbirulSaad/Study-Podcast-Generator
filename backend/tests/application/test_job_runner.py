from datetime import UTC, datetime
from pathlib import Path

from study_podcast.adapters.outbound.in_memory_repositories import (
    InMemoryJobInputSnapshotRepository,
    InMemoryJobRepository,
    InMemoryScriptRepository,
)
from study_podcast.adapters.outbound.tts_fake import FakeTtsEngine
from study_podcast.application.job_runner import GenerationJobRunner
from study_podcast.application.progress import RepositoryProgressReporter
from study_podcast.domain.entities import ActivePodcastScript, AudioChunk, FinalAudio, GenerationJob
from study_podcast.domain.value_objects import JobStatus, ScriptSource


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 6, 14, tzinfo=UTC)


class RunnerStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for_chunk(self, project_id: str, job_id: str, chunk_index: int) -> Path:
        return self.root / project_id / job_id / "chunks" / f"{chunk_index}.wav"

    def path_for_final_audio(self, project_id: str, job_id: str) -> Path:
        return self.root / project_id / job_id / "final.wav"


class FakeMerger:
    def merge(self, *, chunks, output_path: Path) -> FinalAudio:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"RIFF-final")
        return FinalAudio(
            project_id=output_path.parts[-3],
            path=str(output_path),
            duration_seconds=sum(chunk.duration_seconds for chunk in chunks),
            size_bytes=output_path.stat().st_size,
        )


class CancellingTts(FakeTtsEngine):
    def __init__(self, jobs: InMemoryJobRepository, clock: FixedClock) -> None:
        self.jobs = jobs
        self.clock = clock

    def synthesize(
        self,
        *,
        chunk,
        output_path: Path,
        voice_prompt_path=None,
        tts_params=None,
    ) -> AudioChunk:
        audio = super().synthesize(
            chunk=chunk,
            output_path=output_path,
            voice_prompt_path=voice_prompt_path,
            tts_params=tts_params,
        )
        job = self.jobs.list()[0]
        job.request_cancellation(self.clock.now())
        self.jobs.save(job)
        return audio


class ExplodingTts(FakeTtsEngine):
    def synthesize(
        self,
        *,
        chunk,
        output_path: Path,
        voice_prompt_path=None,
        tts_params=None,
    ) -> AudioChunk:
        raise RuntimeError("model failed")


def make_runner(tmp_path: Path, tts=None):
    jobs = InMemoryJobRepository()
    scripts = InMemoryScriptRepository()
    clock = FixedClock()
    job = GenerationJob.create("project-1", clock.now())
    jobs.save(job)
    scripts.save_active(
        ActivePodcastScript(
            project_id="project-1",
            text="[S1] First chunk. Second chunk.",
            source=ScriptSource.PASTED,
            speakers=("S1",),
            updated_at=clock.now(),
        )
    )
    runner = GenerationJobRunner(
        scripts=scripts,
        snapshots=InMemoryJobInputSnapshotRepository(),
        jobs=jobs,
        tts=tts or FakeTtsEngine(),
        merger=FakeMerger(),
        storage=RunnerStorage(tmp_path),
        progress=RepositoryProgressReporter(jobs),
        clock=clock,
        max_chunk_chars=20,
        max_chunks=10,
    )
    return runner, jobs, job


def test_runner_updates_progress_after_each_chunk(tmp_path: Path) -> None:
    runner, jobs, job = make_runner(tmp_path)

    completed = runner.run(job.id)

    assert completed.status is JobStatus.COMPLETED
    assert completed.progress_percent == 100
    assert jobs.get(job.id).completed_chunks == 2
    assert Path(tmp_path / "project-1" / job.id / "final.wav").exists()


def test_runner_checks_cancellation_between_chunks(tmp_path: Path) -> None:
    runner, jobs, job = make_runner(
        tmp_path,
        tts=CancellingTts(InMemoryJobRepository(), FixedClock()),
    )
    runner.tts.jobs = jobs

    cancelled = runner.run(job.id)

    assert cancelled.status is JobStatus.CANCELLED
    assert cancelled.completed_chunks == 1


def test_runner_records_failure_reason(tmp_path: Path) -> None:
    runner, _, job = make_runner(tmp_path, tts=ExplodingTts())

    failed = runner.run(job.id)

    assert failed.status is JobStatus.FAILED
    assert failed.failure_reason == "model failed"
