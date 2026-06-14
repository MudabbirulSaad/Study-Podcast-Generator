# Domain Model

## Entities
- `StudyProject`: id, title, created/updated timestamps.
- `ActivePodcastScript`: project id, raw text, source kind, detected speakers.
- `TextChunk`: order, speaker, text, size estimate.
- `GenerationJob`: progress-tracked generation request.
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
