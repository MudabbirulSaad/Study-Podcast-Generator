from time import sleep

from fastapi.testclient import TestClient

from study_podcast.infrastructure.app import create_app
from study_podcast.infrastructure.config import Settings


def test_project_script_job_and_queue_api_flow(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                max_chunk_chars=20,
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                auto_start_worker_pool=False,
            )
        )
    )

    project_response = client.post("/api/v1/projects", json={"title": "Biology"})
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    script_response = client.put(
        f"/api/v1/projects/{project_id}/script",
        json={"text": "[S1] Cells divide. Tissues grow.", "source": "pasted"},
    )
    assert script_response.status_code == 200
    assert script_response.json()["speakers"] == ["S1"]
    assert len(script_response.json()["chunks"]) == 2

    job_response = client.post(f"/api/v1/projects/{project_id}/jobs")
    assert job_response.status_code == 202
    job = job_response.json()
    assert job["status"] == "queued"
    assert job["progress_percent"] == 0

    duplicate = client.post(f"/api/v1/projects/{project_id}/jobs")
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "code": "active_job_exists",
        "message": "This project already has an active generation job.",
        "details": {"job_id": job["id"]},
    }

    jobs = client.get("/api/v1/jobs").json()
    assert [item["id"] for item in jobs] == [job["id"]]

    queue = client.get("/api/v1/queue").json()
    assert queue["pending_count"] == 1
    assert queue["queue_positions"] == {job["id"]: 1}


def test_projects_are_listed_newest_first_and_detail_includes_summary(tmp_path) -> None:
    settings = Settings(
        max_chunk_chars=20,
        database_path=tmp_path / "app.sqlite3",
        env_file_path=tmp_path / ".env",
        auto_start_worker_pool=False,
    )
    client = TestClient(create_app(settings))
    first = client.post("/api/v1/projects", json={"title": "First"}).json()
    second = client.post("/api/v1/projects", json={"title": "Second"}).json()
    client.put(
        f"/api/v1/projects/{second['id']}/script",
        json={"text": "[Narrator] Restart-safe notes.", "source": "pasted"},
    )
    job = client.post(f"/api/v1/projects/{second['id']}/jobs").json()

    restarted_client = TestClient(create_app(settings))

    projects = restarted_client.get("/api/v1/projects").json()
    detail = restarted_client.get(f"/api/v1/projects/{second['id']}").json()

    assert [project["id"] for project in projects] == [second["id"], first["id"]]
    assert detail["id"] == second["id"]
    assert detail["has_active_script"] is True
    assert detail["latest_jobs"][0]["id"] == job["id"]


def test_project_list_supports_case_insensitive_search(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(database_path=tmp_path / "app.sqlite3", env_file_path=tmp_path / ".env")
        )
    )
    biology = client.post("/api/v1/projects", json={"title": "Biology 101"}).json()
    client.post("/api/v1/projects", json={"title": "Operating Systems"}).json()

    projects = client.get("/api/v1/projects?q=bio").json()

    assert [project["id"] for project in projects] == [biology["id"]]


def test_generation_job_stores_immutable_script_snapshot_and_can_rerun(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                auto_start_worker_pool=False,
                max_chunk_chars=50,
            )
        )
    )
    project_id = client.post("/api/v1/projects", json={"title": "Snapshots"}).json()["id"]
    client.put(
        f"/api/v1/projects/{project_id}/script",
        json={"text": "[S1] Original script.", "source": "pasted"},
    )

    job = client.post(
        f"/api/v1/projects/{project_id}/jobs",
        json={"tts_params": {"temperature": 0.4, "cfg_weight": 0.7}},
    ).json()
    client.post(f"/api/v1/jobs/{job['id']}/cancel")
    client.put(
        f"/api/v1/projects/{project_id}/script",
        json={"text": "[S1] Edited script.", "source": "pasted"},
    )

    snapshot_script = client.get(f"/api/v1/jobs/{job['id']}/script")
    job_detail = client.get(f"/api/v1/jobs/{job['id']}").json()
    rerun = client.post(f"/api/v1/jobs/{job['id']}/rerun").json()
    rerun_script = client.get(f"/api/v1/jobs/{rerun['id']}/script")

    assert snapshot_script.status_code == 200
    assert snapshot_script.json()["text"] == "[S1] Original script."
    assert job_detail["snapshot"]["script_text"] == "[S1] Original script."
    assert job_detail["snapshot"]["tts_params"]["temperature"] == 0.4
    assert rerun["status"] == "queued"
    assert rerun["id"] != job["id"]
    assert rerun_script.json()["text"] == "[S1] Original script."


def test_job_list_supports_search_across_metadata_and_snapshot(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                auto_start_worker_pool=False,
            )
        )
    )
    os_project = client.post("/api/v1/projects", json={"title": "OS"}).json()
    bio_project = client.post("/api/v1/projects", json={"title": "Biology"}).json()
    client.put(
        f"/api/v1/projects/{os_project['id']}/script",
        json={"text": "[S1] Semaphore scheduling notes.", "source": "pasted"},
    )
    client.put(
        f"/api/v1/projects/{bio_project['id']}/script",
        json={"text": "[S1] Cellular respiration.", "source": "pasted"},
    )
    os_job = client.post(f"/api/v1/projects/{os_project['id']}/jobs").json()
    client.post(f"/api/v1/projects/{bio_project['id']}/jobs").json()

    jobs = client.get("/api/v1/jobs?q=semaphore").json()

    assert [job["id"] for job in jobs] == [os_job["id"]]


def test_cancel_job_api(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                auto_start_worker_pool=False,
            )
        )
    )
    project_id = client.post("/api/v1/projects", json={"title": "Chemistry"}).json()["id"]
    client.put(
        f"/api/v1/projects/{project_id}/script",
        json={"text": "Atoms bond.", "source": "pasted"},
    )
    job_id = client.post(f"/api/v1/projects/{project_id}/jobs").json()["id"]

    cancelled = client.post(f"/api/v1/jobs/{job_id}/cancel")

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_txt_upload_saves_active_script(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                max_chunk_chars=20,
                auto_start_worker_pool=False,
            )
        )
    )
    project_id = client.post("/api/v1/projects", json={"title": "Uploaded"}).json()["id"]

    response = client.put(
        f"/api/v1/projects/{project_id}/script",
        files={"file": ("script.txt", b"[S1] Uploaded line. More notes.", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "uploaded"
    assert response.json()["speakers"] == ["S1"]
    assert response.json()["chunks"][0]["text"] == "Uploaded line."


def test_upload_rejects_non_txt_file(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(database_path=tmp_path / "app.sqlite3", env_file_path=tmp_path / ".env")
        )
    )
    project_id = client.post("/api/v1/projects", json={"title": "Upload safety"}).json()["id"]

    response = client.put(
        f"/api/v1/projects/{project_id}/script",
        files={"file": ("script.md", b"# nope", "text/markdown")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": "domain_error",
        "message": "uploaded script must be a .txt file",
        "details": None,
    }


def test_voice_profiles_include_default_and_uploaded_samples_are_safely_stored(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                storage_root=tmp_path / "storage",
            )
        )
    )

    default_voices = client.get("/api/v1/voices").json()
    uploaded = client.post(
        "/api/v1/voices",
        data={"display_name": "My seminar voice"},
        files={"file": ("../../voice.wav", b"RIFFvoice", "audio/wav")},
    )
    voices = client.get("/api/v1/voices").json()

    assert default_voices[0]["id"] == "default"
    assert uploaded.status_code == 201
    assert uploaded.json()["display_name"] == "My seminar voice"
    assert uploaded.json()["source"] == "uploaded"
    assert ".." not in uploaded.json()["sample_path"]
    assert voices[-1]["id"] == uploaded.json()["id"]


def test_voice_upload_rejects_unsupported_file_type(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                storage_root=tmp_path / "storage",
            )
        )
    )

    response = client.post(
        "/api/v1/voices",
        data={"display_name": "Bad voice"},
        files={"file": ("voice.exe", b"nope", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "voice sample must be wav, mp3, flac, or m4a"


def test_api_generates_and_downloads_final_wav_with_fake_engine(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                storage_root=tmp_path / "storage",
                max_chunk_chars=20,
                active_tts_engine="fake",
                enable_dev_tts_engine=True,
            )
        )
    )
    project_id = client.post("/api/v1/projects", json={"title": "Audio"}).json()["id"]
    client.put(
        f"/api/v1/projects/{project_id}/script",
        json={"text": "[S1] Cells divide. Tissues grow.", "source": "pasted"},
    )

    job = client.post(f"/api/v1/projects/{project_id}/jobs").json()
    completed = {}
    for _ in range(20):
        completed = client.get(f"/api/v1/jobs/{job['id']}").json()
        if completed["status"] == "completed":
            break
        sleep(0.05)
    download = client.get(f"/api/v1/projects/{project_id}/audio/final")
    stream = client.get(f"/api/v1/projects/{project_id}/audio/stream")
    job_download = client.get(f"/api/v1/jobs/{job['id']}/audio/final")
    job_stream = client.get(f"/api/v1/jobs/{job['id']}/audio/stream")

    assert completed["status"] == "completed"
    assert download.status_code == 200
    assert download.headers["content-type"] == "audio/wav"
    assert download.headers["cache-control"] == "no-store"
    assert download.content[:4] == b"RIFF"
    assert stream.status_code == 200
    assert stream.headers["cache-control"] == "no-store"
    assert job_download.status_code == 200
    assert job_download.content[:4] == b"RIFF"
    assert job_stream.status_code == 200
    assert job_stream.headers["cache-control"] == "no-store"


def test_missing_resource_uses_error_envelope(tmp_path) -> None:
    client = TestClient(
        create_app(Settings(database_path=":memory:", env_file_path=tmp_path / ".env"))
    )

    response = client.get("/api/v1/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {
        "code": "not_found",
        "message": "job not found",
        "details": None,
    }


def test_domain_error_missing_resource_cases_remain_bad_request(tmp_path) -> None:
    client = TestClient(
        create_app(Settings(database_path=":memory:", env_file_path=tmp_path / ".env"))
    )

    save_script = client.put(
        "/api/v1/projects/missing/script",
        json={"text": "Notes", "source": "pasted"},
    )
    submit_job = client.post("/api/v1/projects/missing/jobs")
    cancel_job = client.post("/api/v1/jobs/missing/cancel")

    assert save_script.status_code == 400
    assert save_script.json() == {
        "code": "domain_error",
        "message": "project not found",
        "details": None,
    }
    assert submit_job.status_code == 400
    assert submit_job.json() == {
        "code": "domain_error",
        "message": "script not found",
        "details": None,
    }
    assert cancel_job.status_code == 400
    assert cancel_job.json() == {
        "code": "domain_error",
        "message": "job not found",
        "details": None,
    }
