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


def _operation(schema: dict, path: str, method: str) -> dict:
    return schema["paths"][path][method]


def _assert_error_response(operation: dict, status_code: str) -> None:
    response = operation["responses"][status_code]
    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }


def test_openapi_uses_stable_operation_ids(tmp_path) -> None:
    schema = _openapi(tmp_path)

    expected_operation_ids = {
        ("post", "/api/v1/projects"): "projects_create",
        ("get", "/api/v1/projects"): "projects_list",
        ("get", "/api/v1/projects/{project_id}"): "projects_get",
        ("put", "/api/v1/projects/{project_id}/script"): "scripts_save",
        ("get", "/api/v1/projects/{project_id}/script"): "scripts_get",
        ("post", "/api/v1/projects/{project_id}/jobs"): "jobs_submit",
        ("get", "/api/v1/jobs"): "jobs_list",
        ("get", "/api/v1/jobs/{job_id}"): "jobs_get",
        ("post", "/api/v1/jobs/{job_id}/cancel"): "jobs_cancel",
        ("post", "/api/v1/jobs/{job_id}/rerun"): "jobs_rerun",
        ("get", "/api/v1/jobs/{job_id}/script"): "jobs_get_script",
        ("get", "/api/v1/queue"): "queue_summary",
        ("get", "/api/v1/projects/{project_id}/audio/final"): "audio_download_project_final",
        ("get", "/api/v1/projects/{project_id}/audio/stream"): "audio_stream_project_final",
        ("get", "/api/v1/jobs/{job_id}/audio/final"): "audio_download_job_final",
        ("get", "/api/v1/jobs/{job_id}/audio/stream"): "audio_stream_job_final",
        ("get", "/api/v1/settings"): "settings_get",
        ("put", "/api/v1/settings"): "settings_update",
        ("post", "/api/v1/settings/reload"): "settings_reload",
        ("get", "/api/v1/settings/runtime-status"): "settings_runtime_status",
        ("get", "/api/v1/settings/tts-engines"): "settings_get_tts_engines",
        ("put", "/api/v1/settings/tts-engine"): "settings_update_tts_engine",
        ("get", "/api/v1/voices"): "voices_list",
        ("post", "/api/v1/voices"): "voices_upload",
    }

    for (method, path), operation_id in expected_operation_ids.items():
        assert _operation(schema, path, method)["operationId"] == operation_id


def test_save_script_documents_json_and_multipart_request_body(tmp_path) -> None:
    schema = _openapi(tmp_path)
    operation = _operation(schema, "/api/v1/projects/{project_id}/script", "put")

    request_body = operation["requestBody"]
    assert request_body["required"] is True

    content = request_body["content"]
    assert set(content) == {"application/json", "multipart/form-data"}
    assert content["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SaveScriptRequest"
    }
    assert (
        schema["components"]["schemas"]["SaveScriptRequest"]["properties"]["text"]["minLength"] == 1
    )
    assert content["multipart/form-data"]["schema"] == {
        "type": "object",
        "required": ["file"],
        "properties": {"file": {"type": "string", "format": "binary"}},
    }


def test_voice_upload_documents_binary_multipart_file(tmp_path) -> None:
    schema = _openapi(tmp_path)
    operation = _operation(schema, "/api/v1/voices", "post")

    multipart = operation["requestBody"]["content"]["multipart/form-data"]["schema"]
    assert operation["requestBody"]["required"] is True
    assert "Body_voices_upload" not in schema["components"]["schemas"]
    assert multipart == {
        "type": "object",
        "required": ["display_name", "file"],
        "properties": {
            "display_name": {"type": "string", "minLength": 1},
            "file": {"type": "string", "format": "binary"},
        },
    }


def test_audio_endpoints_document_wav_binary_and_range_responses(tmp_path) -> None:
    schema = _openapi(tmp_path)
    audio_paths = [
        "/api/v1/projects/{project_id}/audio/final",
        "/api/v1/projects/{project_id}/audio/stream",
        "/api/v1/jobs/{job_id}/audio/final",
        "/api/v1/jobs/{job_id}/audio/stream",
    ]

    for path in audio_paths:
        responses = _operation(schema, path, "get")["responses"]
        assert responses["200"]["content"] == {
            "audio/wav": {"schema": {"type": "string", "format": "binary"}}
        }
        assert responses["206"]["content"] == {
            "audio/wav": {"schema": {"type": "string", "format": "binary"}}
        }
        assert {"Accept-Ranges", "Content-Length"} <= set(responses["200"]["headers"])
        assert {"Accept-Ranges", "Content-Range", "Content-Length"} <= set(
            responses["206"]["headers"]
        )
        assert "Content-Range" in responses["416"]["headers"]
        assert "404" in responses


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
    schema = _openapi(tmp_path)
    documented_errors = [
        ("post", "/api/v1/projects", "400"),
        ("get", "/api/v1/projects/{project_id}", "404"),
        ("put", "/api/v1/projects/{project_id}/script", "400"),
        ("get", "/api/v1/projects/{project_id}/script", "404"),
        ("post", "/api/v1/projects/{project_id}/jobs", "400"),
        ("post", "/api/v1/projects/{project_id}/jobs", "409"),
        ("get", "/api/v1/jobs/{job_id}", "404"),
        ("post", "/api/v1/jobs/{job_id}/cancel", "400"),
        ("post", "/api/v1/jobs/{job_id}/rerun", "400"),
        ("post", "/api/v1/jobs/{job_id}/rerun", "404"),
        ("post", "/api/v1/jobs/{job_id}/rerun", "409"),
        ("get", "/api/v1/jobs/{job_id}/script", "404"),
        ("put", "/api/v1/settings", "400"),
        ("post", "/api/v1/settings/reload", "400"),
        ("put", "/api/v1/settings/tts-engine", "400"),
        ("post", "/api/v1/voices", "400"),
        ("get", "/api/v1/projects/{project_id}/audio/final", "404"),
        ("get", "/api/v1/projects/{project_id}/audio/stream", "404"),
        ("get", "/api/v1/jobs/{job_id}/audio/final", "404"),
        ("get", "/api/v1/jobs/{job_id}/audio/stream", "404"),
    ]

    for method, path, status_code in documented_errors:
        _assert_error_response(_operation(schema, path, method), status_code)

    assert (
        "404" not in _operation(schema, "/api/v1/projects/{project_id}/script", "put")["responses"]
    )
    assert (
        "404" not in _operation(schema, "/api/v1/projects/{project_id}/jobs", "post")["responses"]
    )
    assert "404" not in _operation(schema, "/api/v1/jobs/{job_id}/cancel", "post")["responses"]


def test_safe_numeric_constraints_are_documented(tmp_path) -> None:
    schemas = _openapi(tmp_path)["components"]["schemas"]
    job = schemas["JobResponse"]["properties"]
    queue = schemas["QueueResponse"]["properties"]

    assert job["progress_percent"]["minimum"] == 0
    assert job["progress_percent"]["maximum"] == 100
    assert job["total_chunks"]["minimum"] == 0
    assert job["completed_chunks"]["minimum"] == 0
    assert job["current_chunk_index"]["anyOf"][0]["minimum"] == 0
    assert queue["pending_count"]["minimum"] == 0
    assert queue["running_count"]["minimum"] == 0
    assert queue["completed_count"]["minimum"] == 0
    assert queue["max_active_jobs_total"]["minimum"] == 1
    assert queue["concurrency_limits"]["additionalProperties"]["minimum"] == 0
    assert queue["queue_positions"]["additionalProperties"]["minimum"] == 0


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
