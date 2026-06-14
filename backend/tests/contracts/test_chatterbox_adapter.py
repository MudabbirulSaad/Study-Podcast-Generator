import importlib.util
from pathlib import Path

import pytest

from study_podcast.adapters.outbound.tts_chatterbox import ChatterboxTtsEngine
from study_podcast.domain.entities import TextChunk


def test_chatterbox_adapter_can_be_constructed_without_dependency_installed() -> None:
    adapter = ChatterboxTtsEngine()

    assert adapter.engine_key == "chatterbox"
    assert adapter._model is None


@pytest.mark.skipif(
    importlib.util.find_spec("chatterbox") is None,
    reason="Chatterbox is optional and not installed",
)
def test_chatterbox_adapter_contract_when_dependency_is_available(tmp_path: Path) -> None:
    audio = ChatterboxTtsEngine().synthesize(
        chunk=TextChunk(index=0, speaker="Narrator", text="Short local test."),
        output_path=tmp_path / "chunk.wav",
    )

    assert Path(audio.path).exists()
