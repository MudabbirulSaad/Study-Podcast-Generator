from datetime import UTC, datetime

import pytest

from study_podcast.domain.entities import GenerationJob
from study_podcast.domain.errors import DomainError
from study_podcast.domain.services import detect_speaker_segments, split_script_into_chunks
from study_podcast.domain.value_objects import JobPhase, JobStatus


def test_detects_speaker_tags_and_keeps_narrator_for_untagged_text() -> None:
    segments = detect_speaker_segments("Intro line.\n[S1] Hello there.\n[Narrator] Back to notes.")

    assert [(segment.speaker, segment.text) for segment in segments] == [
        ("Narrator", "Intro line."),
        ("S1", "Hello there."),
        ("Narrator", "Back to notes."),
    ]


def test_chunks_respect_max_size_and_speaker_boundaries() -> None:
    chunks = split_script_into_chunks(
        "[S1] Alpha beta gamma. Delta epsilon.\n[S2] Zeta eta theta.",
        max_chunk_chars=22,
        max_chunks=10,
    )

    assert [(chunk.index, chunk.speaker, chunk.text) for chunk in chunks] == [
        (0, "S1", "Alpha beta gamma."),
        (1, "S1", "Delta epsilon."),
        (2, "S2", "Zeta eta theta."),
    ]


def test_chunking_rejects_too_many_chunks() -> None:
    with pytest.raises(DomainError, match="too many chunks"):
        split_script_into_chunks("One. Two. Three.", max_chunk_chars=5, max_chunks=2)


def test_generation_job_progress_lifecycle() -> None:
    now = datetime(2026, 6, 14, tzinfo=UTC)
    job = GenerationJob.create(project_id="project-1", created_at=now)

    assert job.status is JobStatus.QUEUED
    assert job.phase is JobPhase.QUEUED
    assert job.progress_percent == 0

    job.mark_running(now)
    job.set_chunking(total_chunks=3, now=now)
    job.record_chunk_progress(
        completed_chunks=1,
        current_chunk_index=1,
        current_chunk_preview="First chunk",
        now=now,
    )

    assert job.status is JobStatus.RUNNING
    assert job.phase is JobPhase.SYNTHESIZING
    assert job.progress_percent == 30
    assert job.completed_chunks == 1
    assert job.current_chunk_preview == "First chunk"

    job.mark_merging(now)
    assert job.progress_percent == 95

    job.mark_completed(now)
    assert job.status is JobStatus.COMPLETED
    assert job.phase is JobPhase.COMPLETED
    assert job.progress_percent == 100


def test_terminal_jobs_keep_failure_context() -> None:
    now = datetime(2026, 6, 14, tzinfo=UTC)
    job = GenerationJob.create(project_id="project-1", created_at=now)

    job.mark_running(now)
    job.mark_failed("TTS exploded", now)

    assert job.status is JobStatus.FAILED
    assert job.failure_reason == "TTS exploded"
    assert job.message == "TTS exploded"
