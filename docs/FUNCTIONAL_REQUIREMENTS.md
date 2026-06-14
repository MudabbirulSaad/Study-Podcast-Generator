# Functional Requirements

- Users can create projects and list existing projects.
- Each project has one active script that can be replaced.
- Script input accepts paste and `.txt` upload.
- Uploads are validated by extension, size, and content type where possible.
- Speaker tags are detected and assigned to chunks.
- Jobs are queued through `JobQueue`; routes never synthesize audio inline.
- Multiple jobs may exist across projects.
- Only one active job per project is allowed while status is `queued`, `running`, or `cancel_requested`.
- Job progress includes status, phase, percent, chunk counts, preview, and message.
- Users can cancel queued or running jobs.
- Cancelled queued jobs never start.
- Running jobs check cancellation between chunks.
- Startup recovery marks unfinished jobs as `interrupted`.
- Completed jobs expose final WAV playback and download endpoints.
