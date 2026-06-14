import wave
from collections.abc import Iterable
from pathlib import Path

from study_podcast.domain.entities import AudioChunk, FinalAudio
from study_podcast.domain.errors import DomainError


class WavAudioMerger:
    def merge(self, *, chunks: Iterable[AudioChunk], output_path: Path) -> FinalAudio:
        chunk_list = list(chunks)
        if not chunk_list:
            raise DomainError("no audio chunks to merge")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = output_path.with_suffix(".wav.tmp")
        params = None
        total_duration = 0.0

        with wave.open(str(temp_path), "wb") as destination:
            for chunk in chunk_list:
                with wave.open(chunk.path, "rb") as source:
                    if params is None:
                        params = source.getparams()
                        destination.setparams(params)
                    elif source.getparams()[:3] != params[:3]:
                        raise DomainError("incompatible wav chunk format")
                    destination.writeframes(source.readframes(source.getnframes()))
                total_duration += chunk.duration_seconds

        temp_path.replace(output_path)
        return FinalAudio(
            project_id=output_path.parts[-4] if len(output_path.parts) >= 4 else "",
            path=str(output_path),
            duration_seconds=total_duration,
            size_bytes=output_path.stat().st_size,
        )
