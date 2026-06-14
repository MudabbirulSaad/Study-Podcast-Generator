from pathlib import Path

from study_podcast.domain.entities import AudioChunk, TextChunk


class ChatterboxTtsEngine:
    engine_key = "chatterbox"

    def __init__(self, device: str = "auto") -> None:
        self.device = device
        self._model = None

    def synthesize(self, *, chunk: TextChunk, output_path: Path) -> AudioChunk:
        model = self._load_model()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio = model.generate(chunk.text)
        self._save_wav(audio=audio, output_path=output_path, sample_rate=model.sr)
        return AudioChunk(
            chunk_index=chunk.index,
            path=str(output_path),
            duration_seconds=0.0,
        )

    def _save_wav(self, *, audio, output_path: Path, sample_rate: int) -> None:
        try:
            import soundfile
        except ImportError as exc:
            raise RuntimeError(
                "soundfile is required for Chatterbox WAV output. "
                "Install with `uv sync --extra tts-chatterbox`."
            ) from exc
        audio_data = audio.detach().cpu().squeeze().numpy()
        soundfile.write(
            str(output_path),
            audio_data,
            sample_rate,
            subtype="PCM_16",
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
        self._model = ChatterboxTTS.from_pretrained(device=self._resolve_device())
        return self._model

    def _resolve_device(self) -> str:
        if self.device != "auto":
            return self.device
        try:
            import torch
        except ImportError:
            return "cpu"
        return "cuda" if torch.cuda.is_available() else "cpu"
