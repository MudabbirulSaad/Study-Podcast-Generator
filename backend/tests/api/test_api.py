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


def test_submit_job_preserves_explicit_null_body_behavior(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                auto_start_worker_pool=False,
            )
        )
    )
    project_id = client.post("/api/v1/projects", json={"title": "Null body"}).json()["id"]
    client.put(
        f"/api/v1/projects/{project_id}/script",
        json={"text": "[S1] Explicit null still uses defaults.", "source": "pasted"},
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/jobs",
        content="null",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 202
    assert response.json()["snapshot"]["voice_profile_id"] == "default"
    assert response.json()["snapshot"]["tts_params"] == {}


def test_json_request_bodies_reject_unknown_top_level_fields(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                auto_start_worker_pool=False,
                enable_dev_tts_engine=True,
            )
        )
    )
    project_id = client.post("/api/v1/projects", json={"title": "Strict"}).json()["id"]
    client.put(
        f"/api/v1/projects/{project_id}/script",
        json={"text": "[S1] Strict bodies.", "source": "pasted"},
    )

    responses = [
        client.post("/api/v1/projects", json={"title": "Extra", "extra": True}),
        client.put(
            f"/api/v1/projects/{project_id}/script",
            json={"text": "[S1] Extra.", "source": "pasted", "extra": True},
        ),
        client.post(f"/api/v1/projects/{project_id}/jobs", json={"extra": True}),
        client.put("/api/v1/settings", json={"values": {}, "extra": True}),
        client.put("/api/v1/settings/tts-engine", json={"engine": "fake", "extra": True}),
    ]

    assert [response.status_code for response in responses] == [422, 422, 422, 422, 422]


def test_dynamic_request_maps_remain_extensible(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                auto_start_worker_pool=False,
                enable_dev_tts_engine=True,
            )
        )
    )
    project_id = client.post("/api/v1/projects", json={"title": "Dynamic maps"}).json()["id"]
    client.put(
        f"/api/v1/projects/{project_id}/script",
        json={"text": "[S1] Dynamic maps.", "source": "pasted"},
    )

    job = client.post(
        f"/api/v1/projects/{project_id}/jobs",
        json={"tts_params": {"new_engine_parameter": 0.25}},
    )
    unsupported_setting = client.put(
        "/api/v1/settings",
        json={"values": {"unknown_runtime_setting": "value"}},
    )

    assert job.status_code == 202
    assert job.json()["snapshot"]["tts_params"] == {"new_engine_parameter": 0.25}
    assert unsupported_setting.status_code == 400
    assert unsupported_setting.json() == {
        "code": "domain_error",
        "message": "setting is not editable: unknown_runtime_setting",
        "details": None,
    }


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


def test_job_list_status_and_project_filters_keep_string_compatibility(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                auto_start_worker_pool=False,
            )
        )
    )
    first_project = client.post("/api/v1/projects", json={"title": "First"}).json()
    second_project = client.post("/api/v1/projects", json={"title": "Second"}).json()
    for project in (first_project, second_project):
        client.put(
            f"/api/v1/projects/{project['id']}/script",
            json={"text": "[S1] Filterable.", "source": "pasted"},
        )
    first_job = client.post(f"/api/v1/projects/{first_project['id']}/jobs").json()
    client.post(f"/api/v1/projects/{second_project['id']}/jobs").json()

    queued_or_running = client.get("/api/v1/jobs?status=queued,running")
    unknown_status = client.get("/api/v1/jobs?status=unknown")
    project_match = client.get(f"/api/v1/jobs?project_id={first_project['id']}")
    invalid_project_id = client.get("/api/v1/jobs?project_id=not-a-uuid")

    assert queued_or_running.status_code == 200
    assert len(queued_or_running.json()) == 2
    assert unknown_status.status_code == 200
    assert unknown_status.json() == []
    assert [job["id"] for job in project_match.json()] == [first_job["id"]]
    assert invalid_project_id.status_code == 200
    assert invalid_project_id.json() == []


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


def test_voice_upload_accepts_supported_extension_without_mime_validation(tmp_path) -> None:
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
        data={"display_name": "Generic MIME voice"},
        files={"file": ("voice.wav", b"not really audio", "application/octet-stream")},
    )

    assert response.status_code == 201
    assert response.json()["has_sample"] is True


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
    unsatisfiable_range = client.get(
        f"/api/v1/jobs/{job['id']}/audio/stream",
        headers={"Range": "bytes=999999-1000000"},
    )
    malformed_range = client.get(
        f"/api/v1/jobs/{job['id']}/audio/stream",
        headers={"Range": "items=0-1"},
    )

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
    assert unsatisfiable_range.status_code == 416
    assert unsatisfiable_range.content == b""
    assert unsatisfiable_range.headers["content-range"].startswith("*/")
    assert malformed_range.status_code == 400
    assert malformed_range.headers["content-type"].startswith("text/plain")


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


def test_query_missing_resource_cases_remain_not_found(tmp_path) -> None:
    client = TestClient(
        create_app(Settings(database_path=":memory:", env_file_path=tmp_path / ".env"))
    )

    project = client.get("/api/v1/projects/missing")
    job = client.get("/api/v1/jobs/missing")
    rerun = client.post("/api/v1/jobs/missing/rerun")
    job_script = client.get("/api/v1/jobs/missing/script")

    assert project.status_code == 404
    assert project.json() == {
        "code": "not_found",
        "message": "project not found",
        "details": None,
    }
    assert job.status_code == 404
    assert job.json() == {
        "code": "not_found",
        "message": "job not found",
        "details": None,
    }
    assert rerun.status_code == 404
    assert rerun.json() == {
        "code": "not_found",
        "message": "job snapshot not found",
        "details": None,
    }
    assert job_script.status_code == 404
    assert job_script.json() == {
        "code": "not_found",
        "message": "job snapshot not found",
        "details": None,
    }
