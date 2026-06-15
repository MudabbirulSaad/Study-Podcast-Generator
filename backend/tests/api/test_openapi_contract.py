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


def _resolve_ref(schema: dict, ref: str) -> dict:
    assert ref.startswith("#/")
    current = schema
    for part in ref.removeprefix("#/").split("/"):
        current = current[part]
    return current


def _schema_contains_null(schema: dict) -> bool:
    if schema.get("type") == "null":
        return True
    return any(_schema_contains_null(item) for item in schema.get("anyOf", []))


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

    operation_ids = [
        operation["operationId"]
        for path_item in schema["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    assert len(operation_ids) == len(set(operation_ids))


def test_openapi_schema_local_refs_resolve(tmp_path) -> None:
    schema = _openapi(tmp_path)

    def walk(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if ref is not None:
                _resolve_ref(schema, ref)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)


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
    multipart = content["multipart/form-data"]["schema"]
    assert multipart["required"] == ["file"]
    assert multipart["properties"]["file"]["format"] == "binary"
    assert ".txt" in multipart["properties"]["file"]["description"]
    assert "text/plain" in multipart["properties"]["file"]["description"]
    assert "application/octet-stream" in multipart["properties"]["file"]["description"]
    assert "max_script_size_bytes" in multipart["properties"]["file"]["description"]


def test_voice_upload_documents_binary_multipart_file(tmp_path) -> None:
    schema = _openapi(tmp_path)
    operation = _operation(schema, "/api/v1/voices", "post")

    multipart = operation["requestBody"]["content"]["multipart/form-data"]["schema"]
    assert operation["requestBody"]["required"] is True
    assert "Body_voices_upload" not in schema["components"]["schemas"]
    assert multipart["required"] == ["display_name", "file"]
    assert multipart["properties"]["display_name"]["minLength"] == 1
    assert multipart["properties"]["file"]["format"] == "binary"
    assert ".wav" in multipart["properties"]["file"]["description"]
    assert ".mp3" in multipart["properties"]["file"]["description"]
    assert "MIME type is not validated" in multipart["properties"]["file"]["description"]
    assert "no upload size limit" in multipart["properties"]["file"]["description"]
    assert "sample_path is deprecated" in multipart["properties"]["file"]["description"]


def test_audio_endpoints_document_wav_binary_and_range_responses(tmp_path) -> None:
    schema = _openapi(tmp_path)
    audio_paths = [
        "/api/v1/projects/{project_id}/audio/final",
        "/api/v1/projects/{project_id}/audio/stream",
        "/api/v1/jobs/{job_id}/audio/final",
        "/api/v1/jobs/{job_id}/audio/stream",
    ]

    for path in audio_paths:
        operation = _operation(schema, path, "get")
        parameters = operation["parameters"]
        responses = operation["responses"]
        range_param = next(parameter for parameter in parameters if parameter["in"] == "header")
        assert range_param["name"] == "Range"
        assert range_param["required"] is False
        assert "bytes=" in range_param["schema"]["description"]
        assert responses["200"]["content"] == {
            "audio/wav": {"schema": {"type": "string", "format": "binary"}}
        }
        assert responses["206"]["content"] == {
            "audio/wav": {"schema": {"type": "string", "format": "binary"}}
        }
        assert responses["400"]["content"] == {
            "text/plain": {"schema": {"type": "string", "examples": ["Only support bytes range"]}}
        }
        assert {"Accept-Ranges", "Content-Length"} <= set(responses["200"]["headers"])
        assert {"Accept-Ranges", "Content-Range", "Content-Length"} <= set(
            responses["206"]["headers"]
        )
        assert "Content-Range" in responses["416"]["headers"]
        assert "content" not in responses["416"]
        assert "404" in responses
        assert "WAV" in operation["description"]

    assert (
        "latest completed WAV for the project"
        in _operation(
            schema,
            "/api/v1/projects/{project_id}/audio/final",
            "get",
        )["description"]
    )
    assert (
        "exact job"
        in _operation(
            schema,
            "/api/v1/jobs/{job_id}/audio/final",
            "get",
        )["description"]
    )
    assert (
        "without a download filename"
        in _operation(
            schema,
            "/api/v1/jobs/{job_id}/audio/stream",
            "get",
        )["description"]
    )


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
        _operation(schema, "/api/v1/projects/{project_id}/jobs", "post")["responses"]["409"][
            "content"
        ]["application/json"]["examples"]["active_job_exists"]["value"]["code"]
        == "active_job_exists"
    )
    assert _operation(schema, "/api/v1/jobs/{job_id}", "get")["responses"]["404"]["content"][
        "application/json"
    ]["examples"]["job_not_found"]["value"] == {
        "code": "not_found",
        "message": "job not found",
        "details": None,
    }
    assert (
        _operation(schema, "/api/v1/projects/{project_id}", "get")["responses"]["404"]["content"][
            "application/json"
        ]["examples"]["project_not_found"]["value"]["message"]
        == "project not found"
    )
    assert (
        _operation(schema, "/api/v1/projects", "post")["responses"]["400"]["content"][
            "application/json"
        ]["examples"]["project_title_required"]["value"]["message"]
        == "project title is required"
    )
    cancel_examples = _operation(schema, "/api/v1/jobs/{job_id}/cancel", "post")["responses"][
        "400"
    ]["content"]["application/json"]["examples"]
    assert cancel_examples["job_not_found"]["value"] == {
        "code": "domain_error",
        "message": "job not found",
        "details": None,
    }
    assert cancel_examples["job_cannot_be_cancelled"]["value"]["message"] == (
        "job cannot be cancelled"
    )

    assert (
        "404" not in _operation(schema, "/api/v1/projects/{project_id}/script", "put")["responses"]
    )
    assert (
        "404" not in _operation(schema, "/api/v1/projects/{project_id}/jobs", "post")["responses"]
    )
    assert "404" not in _operation(schema, "/api/v1/jobs/{job_id}/cancel", "post")["responses"]


def test_runtime_settings_schema_documents_typed_values(tmp_path) -> None:
    schemas = _openapi(tmp_path)["components"]["schemas"]
    response_values = schemas["RuntimeSettingsResponse"]["properties"]["values"]
    update_values = schemas["UpdateRuntimeSettingsRequest"]["properties"]["values"]

    settings_values = schemas[response_values["$ref"].split("/")[-1]]
    assert settings_values["properties"]["active_tts_engine"]["type"] == "string"
    assert settings_values["properties"]["storage_root"]["type"] == "string"
    assert settings_values["properties"]["max_chunk_chars"]["type"] == "integer"
    assert settings_values["properties"]["serve_frontend"]["type"] == "boolean"

    additional = update_values["additionalProperties"]
    assert additional is not True
    assert {item["type"] for item in additional["anyOf"]} == {"string", "integer", "boolean"}
    assert update_values["examples"][0]["max_chunk_chars"] == 320
    assert update_values["examples"][0]["serve_frontend"] is False


def test_error_response_details_is_required_but_nullable(tmp_path) -> None:
    error_response = _openapi(tmp_path)["components"]["schemas"]["ErrorResponse"]

    assert {"code", "message", "details"} <= set(error_response["required"])
    assert _schema_contains_null(error_response["properties"]["details"])


def test_json_request_models_reject_unknown_top_level_fields(tmp_path) -> None:
    schemas = _openapi(tmp_path)["components"]["schemas"]

    for name in [
        "CreateProjectRequest",
        "SaveScriptRequest",
        "StartJobRequest",
        "UpdateRuntimeSettingsRequest",
        "UpdateTtsEngineRequest",
    ]:
        assert schemas[name]["additionalProperties"] is False

    assert (
        schemas["StartJobRequest"]["properties"]["tts_params"]["additionalProperties"]["type"]
        == "number"
    )
    update_values = schemas["UpdateRuntimeSettingsRequest"]["properties"]["values"]
    assert {item["type"] for item in update_values["additionalProperties"]["anyOf"]} == {
        "string",
        "integer",
        "boolean",
    }


def test_submit_job_request_body_is_optional_but_not_nullable(tmp_path) -> None:
    schema = _openapi(tmp_path)
    request_body = _operation(schema, "/api/v1/projects/{project_id}/jobs", "post")["requestBody"]

    assert request_body["required"] is False
    body_schema = request_body["content"]["application/json"]["schema"]
    assert body_schema == {"$ref": "#/components/schemas/StartJobRequest"}
    assert not _schema_contains_null(body_schema)
    tts_params = schema["components"]["schemas"]["StartJobRequest"]["properties"]["tts_params"]
    assert tts_params["additionalProperties"]["type"] == "number"
    assert "passed through" in tts_params["description"]
    assert tts_params["examples"][0] == {"temperature": 0.4, "cfg_weight": 0.7}


def test_jobs_list_status_documents_comma_separated_job_status_values(tmp_path) -> None:
    schema = _openapi(tmp_path)
    parameters = _operation(schema, "/api/v1/jobs", "get")["parameters"]
    status_param = next(parameter for parameter in parameters if parameter["name"] == "status")

    assert status_param["required"] is False
    assert "Comma-separated" in status_param["description"]
    assert "queued,running" in status_param["schema"]["examples"]
    assert status_param["schema"]["anyOf"][0]["type"] == "string"
    assert "style" not in status_param
    assert "explode" not in status_param
    assert set(status_param["schema"]["x-accepted-values"]) == set(
        schema["components"]["schemas"]["JobStatus"]["enum"]
    )


def test_jobs_list_project_id_filter_documents_uuid_string_without_validation(tmp_path) -> None:
    schema = _openapi(tmp_path)
    parameters = _operation(schema, "/api/v1/jobs", "get")["parameters"]
    project_id_param = next(
        parameter for parameter in parameters if parameter["name"] == "project_id"
    )

    assert project_id_param["required"] is False
    assert "format" not in project_id_param["schema"]
    assert project_id_param["schema"]["anyOf"][0]["type"] == "string"
    assert "exact string filter" in project_id_param["description"]
    assert "does not validate UUID syntax" in project_id_param["description"]


def test_path_ids_document_uuid_format_without_runtime_uuid_validation(tmp_path) -> None:
    schema = _openapi(tmp_path)
    paths = [
        ("/api/v1/projects/{project_id}", "get", "project_id"),
        ("/api/v1/projects/{project_id}/jobs", "post", "project_id"),
        ("/api/v1/jobs/{job_id}", "get", "job_id"),
        ("/api/v1/jobs/{job_id}/audio/final", "get", "job_id"),
    ]

    for path, method, name in paths:
        parameter = next(
            item
            for item in _operation(schema, path, method)["parameters"]
            if item["in"] == "path" and item["name"] == name
        )
        assert parameter["schema"]["format"] == "uuid"
        assert parameter["schema"]["type"] == "string"


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


def test_job_response_snapshot_is_required_but_nullable(tmp_path) -> None:
    schemas = _openapi(tmp_path)["components"]["schemas"]
    job_response = schemas["JobResponse"]

    assert "snapshot" in job_response["required"]
    assert _schema_contains_null(job_response["properties"]["snapshot"])


def test_voice_profile_deprecates_sample_path_in_favor_of_has_sample(tmp_path) -> None:
    voice = _openapi(tmp_path)["components"]["schemas"]["VoiceProfileResponse"]["properties"]

    assert voice["sample_path"]["deprecated"] is True
    assert "has_sample" in voice["sample_path"]["description"]
    assert voice["has_sample"]["type"] == "boolean"


def test_openapi_includes_global_metadata_and_stable_success_examples(tmp_path) -> None:
    schema = _openapi(tmp_path)

    assert schema["servers"] == [{"url": "/", "description": "Current host"}]
    assert {tag["name"] for tag in schema["tags"]} >= {
        "projects",
        "scripts",
        "jobs",
        "queue",
        "audio",
        "settings",
        "voices",
    }

    examples = [
        (
            "/api/v1/projects",
            "post",
            "201",
            "created_project",
            ("title", "Biology 101"),
        ),
        (
            "/api/v1/projects/{project_id}/script",
            "put",
            "200",
            "saved_script",
            ("source", "pasted"),
        ),
        (
            "/api/v1/projects/{project_id}/jobs",
            "post",
            "202",
            "submitted_job",
            ("status", "queued"),
        ),
        (
            "/api/v1/jobs/{job_id}",
            "get",
            "200",
            "completed_job",
            ("status", "completed"),
        ),
        (
            "/api/v1/settings",
            "get",
            "200",
            "runtime_settings",
            ("runtime_status", "idle"),
        ),
        (
            "/api/v1/voices",
            "post",
            "201",
            "uploaded_voice",
            ("has_sample", True),
        ),
    ]

    for path, method, status_code, example_name, (field, expected) in examples:
        value = _operation(schema, path, method)["responses"][status_code]["content"][
            "application/json"
        ]["examples"][example_name]["value"]
        assert value[field] == expected


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
