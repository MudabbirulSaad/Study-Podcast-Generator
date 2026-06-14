# Architecture

## Style
The backend uses hexagonal architecture. Domain and application layers define the core behavior and ports. FastAPI, SQLite, filesystem, queue workers, and TTS engines are adapters.

## Dependency Direction
- Domain imports only standard library/domain modules.
- Application imports domain entities and ports.
- Inbound and outbound adapters depend inward.
- Infrastructure wires concrete adapters to ports.

## Job Flow
1. API receives `POST /api/v1/projects/{project_id}/jobs`.
2. API validates the active script, creates an immutable job input snapshot, and asks `JobQueue` to submit a job.
3. `JobQueue` persists `queued` state and rejects duplicate active jobs for the same project.
4. `InProcessWorkerPool` pulls queued jobs according to concurrency limits.
5. `JobRunner` executes one job from its snapshot: synthesis, merge, finalization.
6. `ProgressReporter` records progress after phase changes and chunks.
7. API progress endpoints read job state from `JobRepository`.

## Project And Job History
Projects, jobs, snapshots, settings, and voice profiles are stored in SQLite. The active project
script remains editable, while completed jobs keep their original snapshot for inspection and
rerun.

## Voice Profiles
Voice uploads are inbound API concerns backed by filesystem storage and SQLite metadata. The
domain sees a `VoiceProfile` and the application passes its sample path to the TTS port. Chatterbox
maps uploaded profiles to `audio_prompt_path`; the default profile passes no prompt path.

## Startup Recovery
On backend startup, jobs in `queued`, `running`, or `cancel_requested` are marked `interrupted` with message: "Server restarted before this job completed."

## Runtime Settings And Engine Reload
Runtime settings are exposed through an allowlisted API surface. Settings are persisted to SQLite and written to `.env`; startup applies OS environment variables over `.env`, `.env` over SQLite settings, and SQLite settings over code defaults.

FastAPI remains running when settings change. A container-owned runtime reload rebuilds the concrete TTS engine, generation runner, worker pool, and queue concurrency values. Reload is rejected while any job is `queued`, `running`, or `cancel_requested`. If reload fails, the previous working runtime remains active and the failure is reported through the runtime-status API.

Chatterbox is the production-style local engine. The deterministic fake engine is reserved for development and tests and is exposed only when `ENABLE_DEV_TTS_ENGINE=true`.
