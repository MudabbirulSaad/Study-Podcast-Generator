from __future__ import annotations

from study_podcast.domain.entities import (
    ActivePodcastScript,
    GenerationJob,
    JobInputSnapshot,
    StudyProject,
    VoiceProfile,
)


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[str, StudyProject] = {}

    def save(self, project: StudyProject) -> None:
        self.projects[project.id] = project

    def get(self, project_id: str) -> StudyProject | None:
        return self.projects.get(project_id)

    def list(self) -> list[StudyProject]:
        return list(self.projects.values())


class InMemoryScriptRepository:
    def __init__(self) -> None:
        self.scripts: dict[str, ActivePodcastScript] = {}

    def save_active(self, script: ActivePodcastScript) -> None:
        self.scripts[script.project_id] = script

    def get_active(self, project_id: str) -> ActivePodcastScript | None:
        return self.scripts.get(project_id)


class InMemoryJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[str, GenerationJob] = {}

    def save(self, job: GenerationJob) -> None:
        self.jobs[job.id] = job

    def get(self, job_id: str) -> GenerationJob | None:
        return self.jobs.get(job_id)

    def list(self) -> list[GenerationJob]:
        return sorted(self.jobs.values(), key=lambda job: job.created_at)

    def find_active_for_project(self, project_id: str) -> GenerationJob | None:
        return next(
            (job for job in self.list() if job.project_id == project_id and job.status.is_active),
            None,
        )

    def list_unfinished(self) -> list[GenerationJob]:
        return [job for job in self.list() if job.status.is_active]


class InMemoryJobInputSnapshotRepository:
    def __init__(self) -> None:
        self.snapshots: dict[str, JobInputSnapshot] = {}

    def save(self, snapshot: JobInputSnapshot) -> None:
        self.snapshots[snapshot.job_id] = snapshot

    def get(self, job_id: str) -> JobInputSnapshot | None:
        return self.snapshots.get(job_id)


class InMemoryVoiceProfileRepository:
    def __init__(self) -> None:
        self.voices: dict[str, VoiceProfile] = {}

    def save(self, profile: VoiceProfile) -> None:
        self.voices[profile.id] = profile

    def get(self, voice_id: str) -> VoiceProfile | None:
        return self.voices.get(voice_id)

    def list(self) -> list[VoiceProfile]:
        return list(self.voices.values())
