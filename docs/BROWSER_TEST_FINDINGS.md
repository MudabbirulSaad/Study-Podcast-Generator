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

## BUG-004: Chatterbox adapter hardcodes CUDA

- Severity: High
- Status: Fixed
- Environment: local Chatterbox extra on Windows with `torch 2.6.0+cpu`
- Repro:
  1. Install `uv sync --extra tts-chatterbox`.
  2. Run Chatterbox synthesis on a CPU-only Torch install.
- Expected: The adapter uses CUDA only when available, or a configured device such as `cpu`.
- Actual: The adapter always called `ChatterboxTTS.from_pretrained(device="cuda")`, causing `Torch not compiled with CUDA enabled`.

## BUG-005: Chatterbox dependency requires `pkg_resources`

- Severity: Medium
- Status: Fixed
- Environment: `chatterbox-tts==0.1.7`, `resemble-perth==1.0.1`, newer setuptools
- Repro:
  1. Load Chatterbox on Windows with the optional extra installed.
- Expected: Perth watermark dependency imports successfully.
- Actual: `perth.PerthImplicitWatermarker` was `None` because Perth imports `pkg_resources`, which was missing with the installed setuptools version.

## BUG-006: Chatterbox WAV chunks were float WAVs incompatible with stdlib merger

- Severity: High
- Status: Fixed
- Environment: real Chatterbox app job on `http://127.0.0.1:8001`
- Repro:
  1. Run an app generation job with `ACTIVE_TTS_ENGINE=chatterbox`.
  2. Let the job synthesize one chunk and enter merge.
- Expected: The WAV merger reads the generated chunks and produces final audio.
- Actual: Chatterbox chunks were written as 32-bit float WAVs; Python `wave` rejected them during merge with an error similar to `# channels not specified`.

## Passing Checks During Browser Test

- App shell loads from FastAPI at `/`.
- API responds under `/api/v1`.
- Project creation works through the UI.
- Script paste/save works through the UI.
- Speaker and chunk preview works through the UI.
- Fake TTS generation completes and exposes WAV playback/download controls.
- Settings route loads active/available TTS engine information.
- Post-fix `/jobs` renders failed and completed jobs from the API, queue summary, and one copy of each failure message.
- Real Chatterbox synthesis works with `CHATTERBOX_DEVICE=cpu`.
- Real Chatterbox app job completed and served final `audio/wav` output from port `8001`.
