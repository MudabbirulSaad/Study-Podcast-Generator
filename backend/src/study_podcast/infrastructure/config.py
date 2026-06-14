from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    storage_root: Path = Path("data/storage")
    database_path: Path = Path("data/app.sqlite3")
    max_script_size_bytes: int = 1_000_000
    max_chunk_chars: int = 600
    max_chunks: int = 1_000
    fake_tts_max_concurrent_jobs: int = 4
    chatterbox_max_concurrent_jobs: int = 1
    audio_merge_max_concurrent_jobs: int = 1
    max_active_jobs_total: int = 10
    frontend_origin: str = "http://localhost:5173"
    active_tts_engine: str = "fake"

    @property
    def concurrency_limits(self) -> dict[str, int]:
        return {
            "fake": self.fake_tts_max_concurrent_jobs,
            "chatterbox": self.chatterbox_max_concurrent_jobs,
            "merge": self.audio_merge_max_concurrent_jobs,
        }
