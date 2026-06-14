# Study Podcast Generator

Local-first web app for turning `.txt` study podcast scripts into WAV audio podcasts.

## Overview
- Backend: Python, FastAPI, `uv`
- Frontend: React, TypeScript, React Router, Vite
- Architecture: hexagonal ports and adapters
- Production-style TTS engine: Chatterbox, lazy-loaded
- Development/test TTS engine: deterministic fake WAV generator, opt-in only
- Persistent project library, generation history, reusable voice profiles, and custom audio player

## Prerequisites
- Python 3.11 or 3.12
- `uv`
- Node.js and npm

## First-Time Setup
From the repository root:

```bash
cd backend
uv sync
cd ..
npm install
npm --prefix frontend install
```

## Development Mode
Run backend and frontend together with reload:

```bash
npm run dev
```

Development URLs:
- Frontend: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000/api/v1`

In development, Vite proxies `/api` requests to the backend.

## Production-Style Local Mode
Build the frontend once, then let FastAPI serve both the API and compiled UI from one process:

```bash
npm run build
npm run start
```

Open:

```text
http://127.0.0.1:8000
```

## Backend-Only And Frontend-Only
Backend only:

```bash
npm run dev:backend
```

Frontend only:

```bash
npm run dev:frontend
```

## Validation
Run all checks from the repository root:

```bash
npm run check
```

Backend checks:

```bash
cd backend
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run test
npm run build
```

## Chatterbox TTS
Chatterbox is the normal production-style local engine. Install the optional TTS dependencies before generating real audio:

```bash
cd backend
uv sync --extra tts-chatterbox
```

The Chatterbox extra pins a matched CUDA 12.6 PyTorch family from the official PyTorch wheel index:
- `torch==2.11.0`
- `torchaudio==2.11.0`
- `torchvision==0.26.0`

This avoids Windows DLL load errors such as `Could not load ... libtorchaudio.pyd`, which happen when `torch` and `torchaudio` come from different binary generations. Chatterbox currently publishes older Torch pins, so the project uses a uv dependency override for the locally verified CUDA stack.

Run the local app:

```bash
# PowerShell
$env:CHATTERBOX_DEVICE="cpu"
npm run start
```

Use `CHATTERBOX_DEVICE="cuda"` only when the installed PyTorch build has CUDA enabled. The default `CHATTERBOX_DEVICE="auto"` uses CUDA when available and otherwise falls back to CPU.

The real Chatterbox contract test is opt-in because it loads model dependencies:

```bash
cd backend
$env:RUN_CHATTERBOX_TESTS="1"
uv run pytest tests/contracts/test_chatterbox_adapter.py
```

Chatterbox may require a compatible PyTorch/CUDA setup for your GPU. The backend still starts without loading the model; the model is lazy-loaded when the engine is first used. Generated WAV files are written with `soundfile` so local WAV output does not require TorchCodec or FFmpeg.

## Projects, Jobs, And Voices
- Projects are stored in SQLite and listed on the Projects page after restart.
- Each generation job stores an immutable snapshot of the script, detected chunks, selected voice profile, and Chatterbox parameters.
- Completed jobs can be replayed, downloaded, inspected, and rerun from the saved snapshot.
- Uploaded voice samples are saved as reusable local voice profiles under the configured storage root.
- Chatterbox voice cloning uses the saved voice sample as `audio_prompt_path`.
- The UI uses a custom audio player with play/pause, seek, skip, speed, volume, and download controls.

## Runtime Settings
The Settings page edits a safe allowlist of runtime values, including the active TTS engine, Chatterbox device, chunk limits, concurrency limits, storage root, frontend origin, and static frontend serving.

When settings are saved:
- values are persisted to SQLite;
- the project `.env` file is updated;
- the UI shows that a backend engine reload is required.

Use the Settings page reload button to rebuild the TTS runtime inside the running FastAPI process. The frontend polls reload status and does not need a page refresh. Runtime reload is blocked while queued, running, or cancellation-requested jobs exist.

For fast development or tests, enable the deterministic development engine explicitly:

```bash
$env:ENABLE_DEV_TTS_ENGINE="true"
$env:ACTIVE_TTS_ENGINE="fake"
npm run start
```

## Local Data
By default, local metadata and generated audio are written under `backend/data/`. This folder is ignored by git.
