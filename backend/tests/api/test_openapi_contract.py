from fastapi.testclient import TestClient

from study_podcast.infrastructure.app import create_app
from study_podcast.infrastructure.config import Settings


def _client(tmp_path) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "app.sqlite3",
                env_file_path=tmp_path / ".env",
                storage_root=tmp_path / "storage",
                auto_start_worker_pool=False,
            )
        )
    )


def _openapi(tmp_path) -> dict:
    return _client(tmp_path).app.openapi()


def test_save_script_documents_json_and_multipart_request_body(tmp_path) -> None:
    operation = _openapi(tmp_path)["paths"]["/api/v1/projects/{project_id}/script"]["put"]

    request_body = operation["requestBody"]
    assert request_body["required"] is True

    content = request_body["content"]
    assert set(content) == {"application/json", "multipart/form-data"}
    assert content["application/json"]["schema"]["title"] == "SaveScriptRequest"
    assert content["multipart/form-data"]["schema"] == {
        "type": "object",
        "required": ["file"],
        "properties": {"file": {"type": "string", "format": "binary"}},
    }


def test_audio_endpoints_document_wav_binary_success_response(tmp_path) -> None:
    schema = _openapi(tmp_path)
    audio_paths = [
        "/api/v1/projects/{project_id}/audio/final",
        "/api/v1/projects/{project_id}/audio/stream",
        "/api/v1/jobs/{job_id}/audio/final",
        "/api/v1/jobs/{job_id}/audio/stream",
    ]

    for path in audio_paths:
        response_content = schema["paths"][path]["get"]["responses"]["200"]["content"]
        assert response_content == {"audio/wav": {"schema": {"type": "string", "format": "binary"}}}


def test_job_and_script_schemas_expose_stable_enum_values(tmp_path) -> None:
    schemas = _openapi(tmp_path)["components"]["schemas"]

    assert schemas["JobStatus"]["enum"] == [
        "queued",
        "running",
        "cancel_requested",
        "cancelled",
        "failed",
        "interrupted",
        "completed",
    ]
    assert schemas["JobPhase"]["enum"] == [
        "queued",
        "chunking",
        "synthesizing",
        "merging",
        "finalizing",
        "completed",
    ]
    assert schemas["ScriptSource"]["enum"] == ["pasted", "uploaded"]
    assert schemas["JobResponse"]["properties"]["status"]["$ref"].endswith("/JobStatus")
    assert schemas["JobResponse"]["properties"]["phase"]["$ref"].endswith("/JobPhase")
    assert schemas["ScriptResponse"]["properties"]["source"]["$ref"].endswith("/ScriptSource")
    assert schemas["JobSnapshotResponse"]["properties"]["script_source"]["$ref"].endswith(
        "/ScriptSource"
    )


def test_openapi_documents_current_error_response_statuses(tmp_path) -> None:
    paths = _openapi(tmp_path)["paths"]

    assert "400" in paths["/api/v1/projects"]["post"]["responses"]
    assert "404" in paths["/api/v1/projects/{project_id}"]["get"]["responses"]
    assert "400" in paths["/api/v1/projects/{project_id}/script"]["put"]["responses"]
    assert "404" in paths["/api/v1/projects/{project_id}/script"]["get"]["responses"]
    assert "400" in paths["/api/v1/projects/{project_id}/jobs"]["post"]["responses"]
    assert "409" in paths["/api/v1/projects/{project_id}/jobs"]["post"]["responses"]
    assert "404" in paths["/api/v1/jobs/{job_id}"]["get"]["responses"]
    assert "400" in paths["/api/v1/jobs/{job_id}/cancel"]["post"]["responses"]
    assert "404" in paths["/api/v1/jobs/{job_id}/rerun"]["post"]["responses"]
    assert "409" in paths["/api/v1/jobs/{job_id}/rerun"]["post"]["responses"]
    assert "400" in paths["/api/v1/settings"]["put"]["responses"]
    assert "400" in paths["/api/v1/settings/reload"]["post"]["responses"]
    assert "400" in paths["/api/v1/voices"]["post"]["responses"]

    for path in (
        "/api/v1/projects/{project_id}/audio/final",
        "/api/v1/projects/{project_id}/audio/stream",
        "/api/v1/jobs/{job_id}/audio/final",
        "/api/v1/jobs/{job_id}/audio/stream",
    ):
        assert "404" in paths[path]["get"]["responses"]


def test_enum_backed_responses_keep_existing_json_strings(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = client.post("/api/v1/projects", json={"title": "Biology"}).json()["id"]

    script = client.put(
        f"/api/v1/projects/{project_id}/script",
        json={"text": "[S1] Cells divide.", "source": "pasted"},
    )
    job = client.post(f"/api/v1/projects/{project_id}/jobs")

    assert script.status_code == 200
    assert script.json()["source"] == "pasted"
    assert job.status_code == 202
    assert job.json()["status"] == "queued"
    assert job.json()["phase"] == "queued"
    assert job.json()["snapshot"]["script_source"] == "pasted"
