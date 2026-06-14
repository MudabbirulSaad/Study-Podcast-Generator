import importlib.util
import os
from pathlib import Path

import pytest

from study_podcast.adapters.outbound.tts_chatterbox import ChatterboxTtsEngine
from study_podcast.domain.entities import TextChunk


def test_chatterbox_adapter_can_be_constructed_without_dependency_installed() -> None:
    adapter = ChatterboxTtsEngine()

    assert adapter.engine_key == "chatterbox"
    assert adapter.device == "auto"
    assert adapter._model is None


def test_chatterbox_adapter_uses_configured_device() -> None:
    adapter = ChatterboxTtsEngine(device="cpu")

    assert adapter._resolve_device() == "cpu"


def test_chatterbox_adapter_saves_generated_tensor(monkeypatch, tmp_path: Path) -> None:
    saved: dict[str, object] = {}

    class FakeModel:
        sr = 24000

        def generate(self, text: str) -> str:
            return f"audio:{text}"

    class FakeTorchaudio:
        @staticmethod
        def save(
            path: str,
            audio: str,
            sample_rate: int,
            encoding: str,
            bits_per_sample: int,
        ) -> None:
            saved["path"] = path
            saved["audio"] = audio
            saved["sample_rate"] = sample_rate
            saved["encoding"] = encoding
            saved["bits_per_sample"] = bits_per_sample
            Path(path).write_bytes(b"RIFFfake")

    adapter = ChatterboxTtsEngine(device="cpu")
    adapter._model = FakeModel()
    monkeypatch.setitem(__import__("sys").modules, "torchaudio", FakeTorchaudio)

    audio = adapter.synthesize(
        chunk=TextChunk(index=0, speaker="Narrator", text="Short local test."),
        output_path=tmp_path / "chunk.wav",
    )

    assert Path(audio.path).exists()
    assert saved == {
        "path": str(tmp_path / "chunk.wav"),
        "audio": "audio:Short local test.",
        "sample_rate": 24000,
        "encoding": "PCM_S",
        "bits_per_sample": 16,
    }


@pytest.mark.skipif(
    importlib.util.find_spec("chatterbox") is None or os.getenv("RUN_CHATTERBOX_TESTS") != "1",
    reason="Real Chatterbox test is optional; set RUN_CHATTERBOX_TESTS=1 when models are available",
)
def test_chatterbox_adapter_contract_when_dependency_is_available(tmp_path: Path) -> None:
    audio = ChatterboxTtsEngine().synthesize(
        chunk=TextChunk(index=0, speaker="Narrator", text="Short local test."),
        output_path=tmp_path / "chunk.wav",
    )

    assert Path(audio.path).exists()
