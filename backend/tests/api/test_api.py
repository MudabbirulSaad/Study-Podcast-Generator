from fastapi.testclient import TestClient

from study_podcast.infrastructure.app import create_app
from study_podcast.infrastructure.config import Settings


def test_project_script_job_and_queue_api_flow(tmp_path) -> None:
    client = TestClient(
        create_app(
            Settings(
                max_chunk_chars=20,
                database_path=tmp_path / "app.sqlite3",
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


def test_cancel_job_api(tmp_path) -> None:
    client = TestClient(
        create_app(Settings(database_path=tmp_path / "app.sqlite3", auto_start_worker_pool=False))
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


def test_missing_resource_uses_error_envelope() -> None:
    client = TestClient(create_app(Settings(database_path=":memory:")))

    response = client.get("/api/v1/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {
        "code": "not_found",
        "message": "job not found",
        "details": None,
    }
