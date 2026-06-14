# Study Podcast Generator

Local-first web app for turning `.txt` study podcast scripts into WAV audio podcasts.

## Overview
- Backend: Python, FastAPI, `uv`
- Frontend: React, TypeScript, React Router, Vite
- Architecture: hexagonal ports and adapters
- Default TTS engine: deterministic fake WAV generator
- Optional real TTS target: Chatterbox, lazy-loaded

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

## Optional Chatterbox TTS
The app starts and all normal tests pass without Chatterbox installed. To enable the real local adapter:

```bash
cd backend
uv sync --extra tts-chatterbox
```

Run the local app with Chatterbox selected:

```bash
# PowerShell
$env:ACTIVE_TTS_ENGINE="chatterbox"
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

Chatterbox may require a compatible PyTorch/CUDA setup for your GPU. Keep fake TTS as the default while validating the app workflow; switch to Chatterbox only after the local model environment is working.

## Local Data
By default, local metadata and generated audio are written under `backend/data/`. This folder is ignored by git.
