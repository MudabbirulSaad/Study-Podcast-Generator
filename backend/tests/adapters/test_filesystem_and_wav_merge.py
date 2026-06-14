import wave
from pathlib import Path

import pytest

from study_podcast.adapters.outbound.audio_merger_wav import WavAudioMerger
from study_podcast.adapters.outbound.filesystem import LocalFileStorage
from study_podcast.adapters.outbound.tts_fake import FakeTtsEngine
from study_podcast.domain.entities import TextChunk
from study_podcast.domain.errors import DomainError


def test_storage_generates_paths_under_root(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)

    chunk_path = storage.path_for_chunk("project-1", "job-1", 0)
    final_path = storage.path_for_final_audio("project-1", "job-1")

    assert chunk_path.is_relative_to(tmp_path)
    assert final_path.is_relative_to(tmp_path)
    assert chunk_path.name == "0.wav"


def test_storage_rejects_path_traversal_identifiers(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(DomainError, match="unsafe path identifier"):
        storage.path_for_chunk("..", "job-1", 0)


def test_atomic_write_writes_complete_file(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    target = storage.path_for_final_audio("project-1", "job-1")

    storage.write_bytes_atomic(target, b"complete")

    assert target.read_bytes() == b"complete"
    assert not list(target.parent.glob("*.tmp"))


def test_wav_merger_combines_fake_audio_chunks(tmp_path: Path) -> None:
    tts = FakeTtsEngine()
    first = tts.synthesize(
        chunk=TextChunk(index=0, speaker="S1", text="First"),
        output_path=tmp_path / "0.wav",
    )
    second = tts.synthesize(
        chunk=TextChunk(index=1, speaker="S1", text="Second"),
        output_path=tmp_path / "1.wav",
    )

    final = WavAudioMerger().merge(chunks=[first, second], output_path=tmp_path / "final.wav")

    assert Path(final.path).read_bytes()[:4] == b"RIFF"
    with wave.open(final.path, "rb") as wav:
        assert wav.getnframes() > 0
    assert final.size_bytes == Path(final.path).stat().st_size
