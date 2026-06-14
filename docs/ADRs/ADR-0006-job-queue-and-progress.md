# ADR-0006: Job Queue And Progress

## Decision
Use an application `JobQueue` port, a `JobRunner` for one job, an `InProcessWorkerPool` adapter, and a `ProgressReporter` port.

## Consequences
FastAPI handlers return quickly and never synthesize audio inline. Multiple jobs can exist across projects, while duplicate active jobs per project are rejected and real/GPU TTS concurrency defaults to one.
