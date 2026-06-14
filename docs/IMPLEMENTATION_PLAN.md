# Implementation Plan

| # | Goal | Validation | Commit |
|---|---|---|---|
| 1 | Repo init, git, tooling | backend/frontend smoke checks | `chore: initialize repo tooling` |
| 2 | Docs and `AGENTS.md` | doc checklist and checks | `docs: add project blueprint` |
| 3 | Domain model | pytest/ruff/format | `feat: add backend domain model` |
| 4 | Use cases and deterministic dev/test TTS | pytest | `feat: add generation use cases with fake tts` |
| 5 | Job queue and duplicate protection | pytest | `feat: add job queue` |
| 6 | Runner, progress, worker pool | pytest | `feat: add in-process worker pool` |
| 7 | FastAPI routers | pytest/ruff/format | `feat: expose backend api` |
| 8 | Local persistence and startup recovery | pytest | `feat: add sqlite persistence and recovery` |
| 9 | Safe filesystem and WAV merge | pytest | `feat: add safe storage and wav merge` |
| 10 | Chatterbox adapter | pytest without Chatterbox | `feat: add lazy chatterbox adapter` |
| 11 | Frontend shell/routing | typecheck/test/build | `feat: add frontend app shell` |
| 12 | Frontend workflow/progress UI | typecheck/test/build | `feat: add podcast workflow ui` |
| 13 | End-to-end fake local smoke | all checks | `test: add local smoke flow` |
| 14 | Final README/docs acceptance | all checks | `docs: finalize local setup guide` |
| 15 | Runtime settings and Chatterbox-first engine reload | backend/frontend checks | `feat: add runtime tts settings reload` |
