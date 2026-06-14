from datetime import UTC, datetime

from study_podcast.adapters.outbound.persistence_sqlite import (
    SQLiteJobRepository,
    SQLiteProjectRepository,
    SQLiteScriptRepository,
    SQLiteStore,
)
from study_podcast.domain.entities import ActivePodcastScript, GenerationJob, StudyProject
from study_podcast.domain.value_objects import JobStatus, ScriptSource


def test_sqlite_store_round_trips_project_script_and_job(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "app.sqlite3")
    projects = SQLiteProjectRepository(store)
    scripts = SQLiteScriptRepository(store)
    jobs = SQLiteJobRepository(store)
    now = datetime(2026, 6, 14, tzinfo=UTC)
    project = StudyProject.create("History", now)
    script = ActivePodcastScript(
        project_id=project.id,
        text="A script.",
        source=ScriptSource.PASTED,
        speakers=("Narrator",),
        updated_at=now,
    )
    job = GenerationJob.create(project.id, now)
    job.mark_running(now)

    projects.save(project)
    scripts.save_active(script)
    jobs.save(job)

    assert projects.get(project.id) == project
    assert scripts.get_active(project.id) == script
    assert jobs.get(job.id).status is JobStatus.RUNNING
    assert jobs.find_active_for_project(project.id).id == job.id
    assert jobs.list_unfinished()[0].id == job.id
