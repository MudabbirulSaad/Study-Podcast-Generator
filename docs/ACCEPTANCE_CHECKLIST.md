# Acceptance Checklist

- [x] Documentation exists and matches implementation.
- [x] Backend checks pass: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`.
- [x] Frontend checks pass: `npm run typecheck`, `npm run test`, `npm run build`.
- [x] API starts without Chatterbox installed.
- [x] Fake TTS flow creates final WAV.
- [x] Duplicate active job per project is rejected.
- [x] Queue summary reports pending/running/completed jobs.
- [x] Cancellation works for queued and running jobs.
- [x] Startup recovery marks unfinished jobs interrupted.
- [x] Storage paths cannot escape configured storage root.
- [x] Frontend can create project, save/upload script, start job, track progress, and play/download audio.
- [x] Existing projects are listed from SQLite after restart.
- [x] Jobs store immutable script, chunk, voice, and TTS parameter snapshots.
- [x] Completed jobs can be inspected and rerun from their saved snapshot.
- [x] Uploaded voice samples are saved as reusable local voice profiles.
- [x] Chatterbox receives uploaded voice samples through `audio_prompt_path`.
- [x] Frontend uses a custom audio player instead of native browser controls.
