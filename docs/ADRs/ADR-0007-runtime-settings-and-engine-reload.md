# ADR-0007: Runtime Settings And Engine Reload

## Decision
Expose a safe allowlist of runtime settings through the API and Settings page. Persist updates to SQLite and `.env`, then reload the TTS runtime inside the running FastAPI process.

## Context
Users need to adjust Chatterbox device, chunk limits, concurrency, storage path, frontend origin, and related local runtime values without editing files by hand. A full frontend reload is unnecessary because the React app can poll backend runtime status.

## Consequences
- Startup precedence is OS environment variables, `.env`, SQLite settings, then code defaults.
- Runtime reload rebuilds the concrete TTS engine, generation runner, worker pool, and queue concurrency configuration.
- Reload is blocked while jobs are queued, running, or cancellation-requested.
- If reload fails, the previous working runtime remains active and the error is reported through the settings runtime-status API.
- The fake TTS engine is hidden unless `ENABLE_DEV_TTS_ENGINE=true`.
