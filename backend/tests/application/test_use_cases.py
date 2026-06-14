from datetime import UTC, datetime
from pathlib import Path

from study_podcast.adapters.outbound.tts_fake import FakeTtsEngine
from study_podcast.application.use_cases import (
    CreateProject,
    GetScript,
    PreviewChunks,
    SaveActiveScript,
)
from study_podcast.domain.entities import ActivePodcastScript, StudyProject
from study_podcast.domain.value_objects import ScriptSource


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 6, 14, tzinfo=UTC)


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


def test_create_project_and_save_active_script() -> None:
    projects = InMemoryProjectRepository()
    scripts = InMemoryScriptRepository()
    clock = FixedClock()

    project = CreateProject(projects, clock).execute(title=" Biology 101 ")
    saved_script = SaveActiveScript(projects, scripts, clock).execute(
        project_id=project.id,
        text="[S1] Photosynthesis turns light into chemical energy.",
        source=ScriptSource.PASTED,
    )

    assert project.title == "Biology 101"
    assert saved_script.speakers == ("S1",)
    assert GetScript(scripts).execute(project.id) == saved_script


def test_preview_chunks_for_active_script() -> None:
    projects = InMemoryProjectRepository()
    scripts = InMemoryScriptRepository()
    clock = FixedClock()
    project = CreateProject(projects, clock).execute(title="Chemistry")
    SaveActiveScript(projects, scripts, clock).execute(
        project_id=project.id,
        text="[Narrator] Atoms bond. Molecules form.",
        source=ScriptSource.PASTED,
    )

    chunks = PreviewChunks(scripts, max_chunk_chars=20, max_chunks=10).execute(project.id)

    assert [(chunk.index, chunk.speaker, chunk.text) for chunk in chunks] == [
        (0, "Narrator", "Atoms bond."),
        (1, "Narrator", "Molecules form."),
    ]


def test_fake_tts_writes_deterministic_tiny_wav(tmp_path: Path) -> None:
    chunk = PreviewChunks.from_text("Hello test audio.", max_chunk_chars=80, max_chunks=5)[0]
    output = tmp_path / "chunk.wav"

    audio = FakeTtsEngine().synthesize(chunk=chunk, output_path=output)

    assert audio.path == str(output)
    assert output.read_bytes()[:4] == b"RIFF"
    assert output.stat().st_size < 50_000
