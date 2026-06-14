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
```

Frontend:
```bash
cd frontend
npm install
npm run typecheck
npm run test
npm run build
```
