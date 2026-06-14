from pathlib import Path
from uuid import uuid4

from study_podcast.domain.errors import DomainError


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for_chunk(self, project_id: str, job_id: str, chunk_index: int) -> Path:
        self._validate_identifier(project_id)
        self._validate_identifier(job_id)
        path = (
            self.root / "projects" / project_id / "jobs" / job_id / "chunks" / f"{chunk_index}.wav"
        )
        return self._ensure_under_root(path)

    def path_for_final_audio(self, project_id: str, job_id: str) -> Path:
        self._validate_identifier(project_id)
        self._validate_identifier(job_id)
        path = self.root / "projects" / project_id / "jobs" / job_id / "final.wav"
        return self._ensure_under_root(path)

    def path_for_voice_sample(self, voice_id: str, extension: str) -> Path:
        self._validate_identifier(voice_id)
        safe_extension = extension.lower().lstrip(".")
        if safe_extension not in {"wav", "mp3", "flac", "m4a"}:
            raise DomainError("voice sample must be wav, mp3, flac, or m4a")
        path = self.root / "voices" / voice_id / f"sample.{safe_extension}"
        return self._ensure_under_root(path)

    def write_bytes_atomic(self, target: Path, content: bytes) -> None:
        safe_target = self._ensure_under_root(target)
        safe_target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = safe_target.with_name(f"{safe_target.name}.{uuid4()}.tmp")
        temp_path.write_bytes(content)
        temp_path.replace(safe_target)

    def _ensure_under_root(self, path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise DomainError("path escapes storage root")
        return resolved

    def _validate_identifier(self, value: str) -> None:
        if not value or any(part in value for part in ("/", "\\", "..")):
            raise DomainError("unsafe path identifier")
