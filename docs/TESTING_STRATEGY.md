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

Required tests cover chunking, speaker tags, queue behavior, duplicate active jobs, concurrency, cancellation, progress updates, failed jobs, startup recovery, safe paths, API errors, WAV merge, and architecture boundaries.

Real Chatterbox tests are optional and skipped unless dependencies/models are present.

## Frontend
Commands:
```bash
npm run typecheck
npm run test
npm run build
```

Tests cover routes, API client mocks, workflow components, progress display, cancellation states, and audio playback/download controls.
