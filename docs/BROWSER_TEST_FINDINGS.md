# Browser Test Findings

Date: 2026-06-14

## BUG-001: Jobs route does not render existing jobs

- Severity: Medium
- Status: Fixed
- Environment: production-style local runner at `http://127.0.0.1:8000`
- Repro:
  1. Open the app at `http://127.0.0.1:8000`.
  2. Create a project.
  3. Save a script with speaker tags.
  4. Start generation and wait for completion.
  5. Navigate to `/jobs`.
- Expected: The Jobs route lists queued, running, completed, failed, cancelled, and interrupted jobs with phase, progress, chunk counts, queue position when available, and clear messages.
- Actual: The Jobs route only shows the heading and explanatory text, even though `GET /api/v1/jobs` returns jobs.

## BUG-002: Jobs route repeats identical failure text

- Severity: Low
- Status: Fixed
- Environment: production-style local runner at `http://127.0.0.1:8000/jobs`
- Repro:
  1. Open `/jobs` with a failed job where `message` and `failure_reason` have the same text.
- Expected: The failure text is shown once.
- Actual: The same failure text is shown twice.

## BUG-003: Jobs route can hide job history when one API request fails

- Severity: Medium
- Status: Fixed
- Environment: production-style local runner at `http://127.0.0.1:8000/jobs`
- Repro:
  1. Open `/jobs`.
  2. Let either the queue summary request fail or return a non-JSON server error.
- Expected: Job history still renders if `GET /api/v1/jobs` succeeds, and the UI shows a clear error message for the failed secondary request.
- Actual: The route can stay on "No generation jobs yet" and the browser console can show an unhandled JSON parse error.

## Passing Checks During Browser Test

- App shell loads from FastAPI at `/`.
- API responds under `/api/v1`.
- Project creation works through the UI.
- Script paste/save works through the UI.
- Speaker and chunk preview works through the UI.
- Fake TTS generation completes and exposes WAV playback/download controls.
- Settings route loads active/available TTS engine information.
- Post-fix `/jobs` renders failed and completed jobs from the API, queue summary, and one copy of each failure message.
