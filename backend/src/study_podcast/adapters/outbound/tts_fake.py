import wave
from pathlib import Path

from study_podcast.domain.entities import AudioChunk, TextChunk


class FakeTtsEngine:
    engine_key = "fake"

    def synthesize(
        self,
        *,
        chunk: TextChunk,
        output_path: Path,
        voice_prompt_path=None,
        tts_params: dict[str, float] | None = None,
    ) -> AudioChunk:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration_seconds = 0.05
        sample_rate = 8_000
        frame_count = int(sample_rate * duration_seconds)
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"\x00\x00" * frame_count)
        return AudioChunk(
            chunk_index=chunk.index,
            path=str(output_path),
            duration_seconds=duration_seconds,
        )
