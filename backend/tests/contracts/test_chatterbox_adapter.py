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

    class FakeAudio:
        def detach(self):
            return self

        def cpu(self):
            return self

        def squeeze(self):
            return self

        def numpy(self):
            return [0.0, 0.0]

    class FakeModel:
        sr = 24000

        def generate(self, text: str) -> FakeAudio:
            saved["text"] = text
            return FakeAudio()

    class FakeSoundFile:
        @staticmethod
        def write(
            path: str,
            audio,
            sample_rate: int,
            subtype: str,
        ) -> None:
            saved["path"] = path
            saved["audio"] = audio
            saved["sample_rate"] = sample_rate
            saved["subtype"] = subtype
            Path(path).write_bytes(b"RIFFfake")

    adapter = ChatterboxTtsEngine(device="cpu")
    adapter._model = FakeModel()
    monkeypatch.setitem(__import__("sys").modules, "soundfile", FakeSoundFile)

    audio = adapter.synthesize(
        chunk=TextChunk(index=0, speaker="Narrator", text="Short local test."),
        output_path=tmp_path / "chunk.wav",
    )

    assert Path(audio.path).exists()
    assert saved == {
        "text": "Short local test.",
        "path": str(tmp_path / "chunk.wav"),
        "audio": [0.0, 0.0],
        "sample_rate": 24000,
        "subtype": "PCM_16",
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
