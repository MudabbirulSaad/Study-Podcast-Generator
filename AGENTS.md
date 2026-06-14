# Agent Instructions

## Project Rules
- Build a local-first TTS study podcast generator with a FastAPI backend and React TypeScript frontend.
- Keep backend architecture hexagonal: domain and application code must not depend on FastAPI, SQLite, filesystem adapters, or TTS libraries.
- Use one active script per project in v1.
- Use WAV output in v1. MP3 and FFmpeg are out of scope until explicitly added.
- Do not run TTS generation inside FastAPI route handlers. Routes submit jobs through the queue.
- Keep fake TTS deterministic and available without GPU or model downloads.

## Backend Commands
- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format --check .`

## Frontend Commands
- `npm run typecheck`
- `npm run test`
- `npm run build`

## Root Commands
- `npm run dev` starts backend and frontend together for development.
- `npm run build` builds the production-style frontend bundle.
- `npm run start` serves the built frontend and API from one FastAPI process.
- `npm run check` runs backend and frontend validation.

## TDD And Commits
- Work milestone by milestone.
- Write behavior tests through public interfaces before implementation.
- Run checks before every commit.
- Commit only when checks are green.
- Do not let optional Chatterbox dependencies block fake-engine development.
