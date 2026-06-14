# ADR-0008: Job Snapshots And Voice Profiles

## Status
Accepted

## Context
Users need to edit a project script after generation without changing what an earlier job produced.
They also need reusable Chatterbox voice cloning samples so the same voice can be selected without
uploading it for every generation.

## Decision
Each generation job stores an immutable input snapshot containing script text, detected speakers,
chunks, selected voice profile, and TTS parameters. Rerun creates a new queued job from the saved
snapshot.

Voice profiles are stored as SQLite metadata. The built-in `default` profile has no sample path.
Uploaded profiles are stored under the configured local storage root with app-generated IDs and are
passed to Chatterbox as `audio_prompt_path`.

## Consequences
- Job history remains truthful even when the active project script changes.
- Reruns are exact with respect to script, voice selection, and TTS parameters.
- Uploaded voice samples become local reusable assets.
- The fake TTS adapter must accept the same voice/parameter inputs as Chatterbox so normal tests
  remain deterministic and GPU-free.
