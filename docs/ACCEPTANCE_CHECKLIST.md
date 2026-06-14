# Acceptance Checklist

- [ ] Documentation exists and matches implementation.
- [ ] Backend checks pass.
- [ ] Frontend checks pass.
- [ ] API starts without Chatterbox installed.
- [ ] Fake TTS flow creates final WAV.
- [ ] Duplicate active job per project is rejected.
- [ ] Queue summary reports pending/running/completed jobs.
- [ ] Cancellation works for queued and running jobs.
- [ ] Startup recovery marks unfinished jobs interrupted.
- [ ] Storage paths cannot escape configured storage root.
- [ ] Frontend can create project, save script, start job, track progress, and play/download audio.
