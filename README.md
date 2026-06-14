# Study Podcast Generator

Local-first web app for turning `.txt` study podcast scripts into WAV audio podcasts.

## Stack
- Backend: Python, FastAPI, `uv`
- Frontend: React, TypeScript, React Router, Vite
- Architecture: hexagonal ports and adapters
- Default TTS for development/tests: deterministic fake WAV generator
- Optional real TTS target: Chatterbox, lazy-loaded

## Development
Backend:
```bash
cd backend
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run uvicorn study_podcast.infrastructure.app:create_app --factory --reload
```

Frontend:
```bash
cd frontend
npm install
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

Chatterbox may require a compatible PyTorch/CUDA setup for your GPU. Keep fake TTS as the default while validating the app workflow; switch to Chatterbox only after the local model environment is working.
