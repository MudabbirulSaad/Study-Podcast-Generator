from dataclasses import dataclass
from typing import Protocol

from study_podcast.domain.entities import ActivePodcastScript, StudyProject, TextChunk
from study_podcast.domain.errors import DomainError
from study_podcast.domain.ports import ProjectRepository, ScriptRepository
from study_podcast.domain.services import detect_speaker_segments, split_script_into_chunks
from study_podcast.domain.value_objects import ScriptSource


class Clock(Protocol):
    def now(self): ...


@dataclass(frozen=True)
class CreateProject:
    projects: ProjectRepository
    clock: Clock

    def execute(self, *, title: str) -> StudyProject:
        clean_title = title.strip()
        if not clean_title:
            raise DomainError("project title is required")
        project = StudyProject.create(title=clean_title, now=self.clock.now())
        self.projects.save(project)
        return project


@dataclass(frozen=True)
class SaveActiveScript:
    projects: ProjectRepository
    scripts: ScriptRepository
    clock: Clock

    def execute(
        self,
        *,
        project_id: str,
        text: str,
        source: ScriptSource,
    ) -> ActivePodcastScript:
        if self.projects.get(project_id) is None:
            raise DomainError("project not found")
        clean_text = text.strip()
        if not clean_text:
            raise DomainError("script text is required")
        speakers = tuple(
            dict.fromkeys(segment.speaker for segment in detect_speaker_segments(clean_text))
        )
        script = ActivePodcastScript(
            project_id=project_id,
            text=clean_text,
            source=source,
            speakers=speakers,
            updated_at=self.clock.now(),
        )
        self.scripts.save_active(script)
        return script


@dataclass(frozen=True)
class GetScript:
    scripts: ScriptRepository

    def execute(self, project_id: str) -> ActivePodcastScript | None:
        return self.scripts.get_active(project_id)


@dataclass(frozen=True)
class PreviewChunks:
    scripts: ScriptRepository
    max_chunk_chars: int
    max_chunks: int

    def execute(self, project_id: str) -> list[TextChunk]:
        script = self.scripts.get_active(project_id)
        if script is None:
            raise DomainError("script not found")
        return self.from_text(
            script.text,
            max_chunk_chars=self.max_chunk_chars,
            max_chunks=self.max_chunks,
        )

    @staticmethod
    def from_text(text: str, *, max_chunk_chars: int, max_chunks: int) -> list[TextChunk]:
        return split_script_into_chunks(
            text,
            max_chunk_chars=max_chunk_chars,
            max_chunks=max_chunks,
        )
