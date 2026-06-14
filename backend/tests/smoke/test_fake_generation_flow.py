from pathlib import Path

from study_podcast.application.use_cases import CreateProject, SaveActiveScript
from study_podcast.domain.value_objects import JobStatus, ScriptSource
from study_podcast.infrastructure.config import Settings
from study_podcast.infrastructure.container import Container


def test_fake_local_generation_flow_creates_final_wav(tmp_path: Path) -> None:
    container = Container.create(
        Settings(
            database_path=tmp_path / "app.sqlite3",
            env_file_path=tmp_path / ".env",
            storage_root=tmp_path / "storage",
            max_chunk_chars=24,
            active_tts_engine="fake",
            enable_dev_tts_engine=True,
        )
    )
    project = CreateProject(container.projects, container.clock).execute(title="Biology")
    SaveActiveScript(container.projects, container.scripts, container.clock).execute(
        project_id=project.id,
        text="[S1] Cells divide. [Narrator] Tissues grow.",
        source=ScriptSource.PASTED,
    )
    job = container.queue.submit_generation_job(project.id)

    completed = container.runner.run(job.id)

    assert completed.status is JobStatus.COMPLETED
    final_path = container.storage.path_for_final_audio(project.id, job.id)
    assert final_path.exists()
    assert final_path.read_bytes()[:4] == b"RIFF"
