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
- `GET /settings/tts-engines`
- `PUT /settings/tts-engine`

## Error Envelope
```json
{
  "code": "error_code",
  "message": "Human readable message.",
  "details": {}
}
```
