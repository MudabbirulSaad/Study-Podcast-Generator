# Domain Model

## Entities
- `StudyProject`: id, title, created/updated timestamps.
- `ActivePodcastScript`: project id, raw text, source kind, detected speakers.
- `TextChunk`: order, speaker, text, size estimate.
- `GenerationJob`: progress-tracked generation request.
- `JobInputSnapshot`: immutable script, chunk, voice, and TTS parameter inputs used by one job.
- `VoiceProfile`: default Chatterbox voice or uploaded reusable voice sample.
- `AudioChunk`: generated WAV chunk.
- `FinalAudio`: merged WAV artifact.
- `QueueSummary`: pending/running/completed counts and concurrency.

## Job Statuses
- `queued`
- `running`
- `cancel_requested`
- `cancelled`
- `failed`
- `interrupted`
- `completed`

## Job Phases
- `queued`
- `chunking`
- `synthesizing`
- `merging`
- `finalizing`
- `completed`

## Progress
Queued jobs start at `0`. Chunking sets `total_chunks`. Synthesis progress follows completed chunks. Merge/finalize reserve the final 5-10%. Terminal failure states retain last known progress and message. Completed jobs reach `100`.

## Snapshots And Reruns
Generation reads from the job snapshot when present, not from the mutable active project script.
Editing a project script after a job starts does not change that job. Rerun creates a new queued
job from the old snapshot.

## Voice Profiles
The `default` voice has no sample path. Uploaded profiles store a local sample path under the
configured storage root and are passed to Chatterbox as `audio_prompt_path`.
