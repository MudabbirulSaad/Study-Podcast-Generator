# Testing Strategy

## Principles
- Use TDD with vertical slices.
- Test behavior through public interfaces.
- Mock only system boundaries.
- Normal tests must be fast and deterministic.

## Backend
Commands:
```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Required tests cover chunking, speaker tags, queue behavior, duplicate active jobs, concurrency, cancellation, progress updates, failed jobs, startup recovery, safe paths, API errors, WAV merge, runtime settings persistence, runtime engine reload, and architecture boundaries.

Fake TTS is explicit dev/test infrastructure. Real Chatterbox tests are optional and skipped unless dependencies/models are present.

## Frontend
Commands:
```bash
npm run typecheck
npm run test
npm run build
```

Tests cover routes, API client mocks, workflow components, progress display, cancellation states, audio playback/download controls, settings editing, reload-required state, runtime polling, and reload failure display.
