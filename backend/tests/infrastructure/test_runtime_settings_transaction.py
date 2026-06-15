from study_podcast.infrastructure.config import Settings
from study_podcast.infrastructure.container import Container
from study_podcast.infrastructure.runtime_settings_transaction import RuntimeSettingsTransaction


def test_runtime_settings_transaction_persists_and_marks_reload_required(tmp_path) -> None:
    container = Container.create(
        Settings(
            database_path=tmp_path / "app.sqlite3",
            env_file_path=tmp_path / ".env",
            storage_root=tmp_path / "storage",
            enable_dev_tts_engine=True,
            auto_start_worker_pool=False,
        )
    )
    transaction = RuntimeSettingsTransaction(container)

    transaction.update(
        {
            "active_tts_engine": "fake",
            "max_chunk_chars": 320,
            "serve_frontend": False,
        }
    )

    assert container.settings.active_tts_engine == "fake"
    assert container.settings.max_chunk_chars == 320
    assert container.settings.serve_frontend is False
    assert container.reload_required is True
    assert container.runtime_status == "reload_pending"
    assert container.settings_repo.list()["active_tts_engine"] == "fake"
    env_text = container.settings.env_file_path.read_text()
    assert "ACTIVE_TTS_ENGINE=fake" in env_text
    assert "MAX_CHUNK_CHARS=320" in env_text
    assert "SERVE_FRONTEND=false" in env_text
