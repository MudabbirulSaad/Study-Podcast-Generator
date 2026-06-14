# Product Requirements Document

## Product
Study Podcast Generator is a local-first app that converts a `.txt` study podcast script into a WAV podcast on the user's machine.

## User Goal
The user can generate a script from course material in ChatGPT/Codex, paste or upload it, and locally synthesize audio for offline listening.

## Success Criteria
- Create and open study podcast projects.
- Store one active script per project.
- Detect optional speaker tags such as `[S1]`, `[S2]`, and `[Narrator]`.
- Chunk long text safely for local TTS.
- Queue generation jobs across projects with clear progress.
- Generate deterministic fake WAVs in tests without GPU/model dependencies.
- Optionally enable Chatterbox without breaking app startup when it is absent.
- Play or download the final WAV.
