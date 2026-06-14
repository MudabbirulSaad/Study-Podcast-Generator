# Non-Functional Requirements

- Backend starts without Chatterbox installed.
- Normal tests pass without GPU, Chatterbox, or model downloads.
- Fake TTS output is deterministic and tiny.
- Real/GPU TTS concurrency defaults to one job.
- CORS is restricted to the configured local frontend origin.
- Storage paths use app-generated IDs and `pathlib`.
- Files are stored only under the configured storage directory.
- Generated files are written to temporary paths and atomically renamed.
- Script size, chunk size, chunk count, and output size are configurable.
- User text, filenames, and generated content are never executed as code or shell commands.
