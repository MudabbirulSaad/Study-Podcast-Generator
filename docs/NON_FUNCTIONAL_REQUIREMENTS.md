# Non-Functional Requirements

- Backend starts without Chatterbox installed.
- Normal tests pass without GPU, Chatterbox, or model downloads.
- Chatterbox is the production-style local TTS engine and is lazy-loaded.
- Fake TTS output is deterministic, tiny, and available only as an explicit dev/test engine.
- Runtime settings are persisted to SQLite and `.env`.
- Runtime engine reload keeps FastAPI running and does not reload the frontend.
- Runtime reload is blocked while jobs are active.
- Real/GPU TTS concurrency defaults to one job.
- CORS is restricted to the configured local frontend origin.
- Storage paths use app-generated IDs and `pathlib`.
- Files are stored only under the configured storage directory.
- Generated files are written to temporary paths and atomically renamed.
- Script size, chunk size, chunk count, and output size are configurable.
- User text, filenames, and generated content are never executed as code or shell commands.
