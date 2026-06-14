from pathlib import Path

from study_podcast.domain.entities import AudioChunk, TextChunk


class ChatterboxTtsEngine:
    engine_key = "chatterbox"

    def __init__(self) -> None:
        self._model = None

    def synthesize(self, *, chunk: TextChunk, output_path: Path) -> AudioChunk:
        model = self._load_model()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio = model.generate(chunk.text)
        model.save_wav(audio, str(output_path))
        return AudioChunk(
            chunk_index=chunk.index,
            path=str(output_path),
            duration_seconds=0.0,
        )

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from chatterbox.tts import ChatterboxTTS
        except ImportError as exc:
            raise RuntimeError(
                "Chatterbox is not installed. Install with `uv sync --extra tts-chatterbox` "
                "and follow the CUDA/PyTorch notes in README.md."
            ) from exc
        self._model = ChatterboxTTS.from_pretrained(device="cuda")
        return self._model
