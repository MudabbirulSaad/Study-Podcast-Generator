from pathlib import Path

from fastapi.testclient import TestClient

from study_podcast.infrastructure.app import create_app
from study_podcast.infrastructure.config import Settings


def _settings(tmp_path: Path, **overrides) -> Settings:
    return Settings(
        database_path=tmp_path / "app.sqlite3",
        storage_root=tmp_path / "storage",
        env_file_path=tmp_path / ".env",
        auto_start_worker_pool=False,
        **overrides,
    )


def test_settings_api_returns_allowlisted_runtime_settings(tmp_path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))

    response = client.get("/api/v1/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["values"]["active_tts_engine"] == "chatterbox"
    assert "fake" not in body["available_engines"]
    assert "active_tts_engine" in body["editable_fields"]
    assert "database_path" not in body["editable_fields"]
    assert body["reload_required"] is False
    assert body["runtime_status"] == "idle"


def test_dev_fake_engine_is_visible_only_when_enabled(tmp_path) -> None:
    hidden = TestClient(create_app(_settings(tmp_path / "hidden")))
    shown = TestClient(create_app(_settings(tmp_path / "shown", enable_dev_tts_engine=True)))

    assert hidden.get("/api/v1/settings").json()["available_engines"] == ["chatterbox"]
    assert shown.get("/api/v1/settings").json()["available_engines"] == ["chatterbox", "fake"]


def test_updating_settings_persists_to_sqlite_and_env_file(tmp_path) -> None:
    settings = _settings(tmp_path, enable_dev_tts_engine=True)
    client = TestClient(create_app(settings))

    response = client.put(
        "/api/v1/settings",
        json={
            "values": {
                "active_tts_engine": "fake",
                "chatterbox_device": "cpu",
                "max_chunk_chars": 320,
                "serve_frontend": False,
            }
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["values"]["active_tts_engine"] == "fake"
    assert body["values"]["max_chunk_chars"] == 320
    assert body["reload_required"] is True
    env_text = settings.env_file_path.read_text()
    assert "ACTIVE_TTS_ENGINE=fake" in env_text
    assert "MAX_CHUNK_CHARS=320" in env_text
    assert "SERVE_FRONTEND=false" in env_text

    restarted = TestClient(create_app(settings))
    assert restarted.get("/api/v1/settings").json()["values"]["active_tts_engine"] == "fake"


def test_settings_update_rejects_hidden_fake_engine(tmp_path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))

    response = client.put("/api/v1/settings", json={"values": {"active_tts_engine": "fake"}})

    assert response.status_code == 400
    assert response.json()["code"] == "domain_error"


def test_settings_update_rejects_unsupported_setting_with_error_envelope(tmp_path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))

    response = client.put("/api/v1/settings", json={"values": {"database_path": "nope"}})

    assert response.status_code == 400
    assert response.json() == {
        "code": "domain_error",
        "message": "setting is not editable: database_path",
        "details": None,
    }


def test_runtime_reload_rejects_when_active_jobs_exist(tmp_path) -> None:
    client = TestClient(create_app(_settings(tmp_path, enable_dev_tts_engine=True)))
    project_id = client.post("/api/v1/projects", json={"title": "Reload block"}).json()["id"]
    client.put(
        f"/api/v1/projects/{project_id}/script",
        json={"text": "A queued job blocks reload.", "source": "pasted"},
    )
    client.post(f"/api/v1/projects/{project_id}/jobs")
    client.put("/api/v1/settings", json={"values": {"active_tts_engine": "fake"}})

    response = client.post("/api/v1/settings/reload")

    assert response.status_code == 400
    assert response.json() == {
        "code": "domain_error",
        "message": "runtime reload requires all active jobs to finish or be cancelled",
        "details": None,
    }


def test_runtime_reload_swaps_engine_without_restarting_fastapi(tmp_path) -> None:
    client = TestClient(create_app(_settings(tmp_path, enable_dev_tts_engine=True)))
    client.put("/api/v1/settings", json={"values": {"active_tts_engine": "fake"}})

    response = client.post("/api/v1/settings/reload")

    assert response.status_code == 202
    status = client.get("/api/v1/settings/runtime-status").json()
    assert status["status"] == "ready"
    assert status["active_engine"] == "fake"
    assert client.get("/api/v1/projects").status_code == 200


def test_runtime_reload_failure_preserves_previous_runtime(tmp_path) -> None:
    client = TestClient(create_app(_settings(tmp_path, enable_dev_tts_engine=True)))
    client.put("/api/v1/settings", json={"values": {"active_tts_engine": "unknown"}})

    response = client.post("/api/v1/settings/reload")

    assert response.status_code == 400
    status = client.get("/api/v1/settings/runtime-status").json()
    assert status["status"] == "failed"
    assert status["active_engine"] == "chatterbox"
    assert "unknown" in status["last_reload_error"]
