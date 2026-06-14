# API Contract

Base path: `/api/v1`

## Projects
- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`

## Active Script
- `PUT /projects/{project_id}/script`
- `GET /projects/{project_id}/script`

V1 supports one active script per project. Multiple script versions are reserved for v2.

## Jobs And Queue
- `POST /projects/{project_id}/jobs`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/cancel`
- `GET /queue`

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
