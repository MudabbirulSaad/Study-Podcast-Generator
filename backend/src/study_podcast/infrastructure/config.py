from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE_PATH = REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, extra="ignore")

    storage_root: Path = Path("data/storage")
    database_path: Path = Path("data/app.sqlite3")
    env_file_path: Path = ENV_FILE_PATH
    max_script_size_bytes: int = 1_000_000
    max_chunk_chars: int = 600
    max_chunks: int = 1_000
    fake_tts_max_concurrent_jobs: int = 4
    chatterbox_max_concurrent_jobs: int = 1
    audio_merge_max_concurrent_jobs: int = 1
    max_active_jobs_total: int = 10
    auto_start_worker_pool: bool = True
    serve_frontend: bool = True
    frontend_dist_path: Path = REPO_ROOT / "frontend" / "dist"
    frontend_origin: str = "http://localhost:5173"
    active_tts_engine: str = "chatterbox"
    enable_dev_tts_engine: bool = False
    chatterbox_device: str = "auto"

    @property
    def concurrency_limits(self) -> dict[str, int]:
        return {
            "fake": self.fake_tts_max_concurrent_jobs,
            "chatterbox": self.chatterbox_max_concurrent_jobs,
            "merge": self.audio_merge_max_concurrent_jobs,
        }
