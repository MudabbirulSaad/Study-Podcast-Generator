from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"

    @property
    def is_active(self) -> bool:
        return self in {self.QUEUED, self.RUNNING, self.CANCEL_REQUESTED}


class JobPhase(StrEnum):
    QUEUED = "queued"
    CHUNKING = "chunking"
    SYNTHESIZING = "synthesizing"
    MERGING = "merging"
    FINALIZING = "finalizing"
    COMPLETED = "completed"


class ScriptSource(StrEnum):
    PASTED = "pasted"
    UPLOADED = "uploaded"
