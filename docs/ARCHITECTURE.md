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
2. Use case validates the project/script and asks `JobQueue` to submit a job.
3. `JobQueue` persists `queued` state and rejects duplicate active jobs for the same project.
4. `InProcessWorkerPool` pulls queued jobs according to concurrency limits.
5. `JobRunner` executes one job: chunking, synthesis, merge, finalization.
6. `ProgressReporter` records progress after phase changes and chunks.
7. API progress endpoints read job state from `JobRepository`.

## Startup Recovery
On backend startup, jobs in `queued`, `running`, or `cancel_requested` are marked `interrupted` with message: "Server restarted before this job completed."
