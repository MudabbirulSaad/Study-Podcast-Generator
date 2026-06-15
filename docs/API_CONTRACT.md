# API Contract

Base path: `/api/v1`

## Projects
- `POST /projects`
- `GET /projects?q=<text>` returns persisted projects newest first, optionally filtering by
  case-insensitive title search.
- `GET /projects/{project_id}` returns project details, active-script presence, and latest jobs.

## Active Script
- `PUT /projects/{project_id}/script`
- `GET /projects/{project_id}/script`

V1 supports one active script per project. Multiple script versions are reserved for v2.

## Jobs And Queue
- `POST /projects/{project_id}/jobs` accepts optional `voice_profile_id` and `tts_params`.
- `GET /jobs?status=completed&project_id=<id>&q=<text>` lists jobs with optional filters.
  Search matches job id, project id, status, phase, message, failure reason, and saved snapshot
  script text.
- `GET /jobs/{job_id}` returns progress plus snapshot summary when available.
- `POST /jobs/{job_id}/cancel`
- `POST /jobs/{job_id}/rerun`
- `GET /jobs/{job_id}/script`
- `GET /queue`

Each submitted generation job stores an immutable input snapshot containing script text,
detected chunks/speakers, selected voice profile, and Chatterbox parameters.

Duplicate active job response:
```json
{
  "code": "active_job_exists",
  "message": "This project already has an active generation job.",
  "details": {
    "job_id": "<existing_job_id>"
  }
}
```

## Audio
- `GET /projects/{project_id}/audio/final`
- `GET /projects/{project_id}/audio/stream`
- `GET /jobs/{job_id}/audio/final`
- `GET /jobs/{job_id}/audio/stream`

Project audio endpoints return the latest completed job for compatibility. New UI flows use
job-specific audio endpoints.

## Voices
- `GET /voices`
- `POST /voices`

`GET /voices` always includes the built-in `default` Chatterbox voice. Uploaded voices are saved
locally as reusable profiles and used as Chatterbox `audio_prompt_path` values.

## Settings
- `GET /settings`
- `PUT /settings`
- `POST /settings/reload`
- `GET /settings/runtime-status`
- `GET /settings/tts-engines` remains as a compatibility read.
- `PUT /settings/tts-engine` remains as a compatibility write.

`GET /settings` returns:
```json
{
  "values": {
    "active_tts_engine": "chatterbox",
    "chatterbox_device": "auto"
  },
  "editable_fields": ["active_tts_engine", "chatterbox_device"],
  "available_engines": ["chatterbox"],
  "reload_required": false,
  "runtime_status": "idle",
  "last_reload_error": null
}
```

`PUT /settings` accepts an allowlisted partial `values` object. It persists settings to SQLite and `.env`, then returns `reload_required: true`.

`POST /settings/reload` rebuilds the backend TTS runtime without restarting FastAPI. It returns `400` if jobs are `queued`, `running`, or `cancel_requested`.

`GET /settings/runtime-status` returns the current runtime status: `idle`, `reload_pending`, `reloading`, `ready`, or `failed`.

## Error Envelope
```json
{
  "code": "error_code",
  "message": "Human readable message.",
  "details": {}
}
```
