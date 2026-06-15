from datetime import UTC, datetime

from study_podcast.adapters.outbound.filesystem import LocalFileStorage
from study_podcast.adapters.outbound.in_memory_repositories import (
    InMemoryJobInputSnapshotRepository,
    InMemoryJobRepository,
    InMemoryProjectRepository,
    InMemoryScriptRepository,
)
from study_podcast.application.job_queue import DefaultJobQueue
from study_podcast.application.read_models import AudioReadModel, JobReadModel, ProjectReadModel
from study_podcast.domain.entities import ActivePodcastScript, JobInputSnapshot, StudyProject
from study_podcast.domain.value_objects import ScriptSource


class FixedClock:
    def now(self):
        return datetime(2026, 6, 15, tzinfo=UTC)


def test_project_read_model_filters_and_returns_detail_summary() -> None:
    clock = FixedClock()
    projects = InMemoryProjectRepository()
    scripts = InMemoryScriptRepository()
    jobs = InMemoryJobRepository()
    biology = StudyProject.create(title="Biology 101", now=clock.now())
    systems = StudyProject.create(title="Operating Systems", now=clock.now())
    projects.save(biology)
    projects.save(systems)
    scripts.save_active(
        ActivePodcastScript(
            project_id=systems.id,
            text="[S1] Scheduling.",
            source=ScriptSource.PASTED,
            speakers=("S1",),
            updated_at=clock.now(),
        )
    )
    job = DefaultJobQueue(jobs=jobs, clock=clock, max_active_jobs_total=10).submit_generation_job(
        systems.id
    )

    read_model = ProjectReadModel(projects=projects, scripts=scripts, jobs=jobs)
    detail = read_model.get_detail(systems.id)

    assert [project.id for project in read_model.list(q="bio")] == [biology.id]
    assert detail.project.id == systems.id
    assert detail.has_active_script is True
    assert [item.id for item in detail.latest_jobs] == [job.id]


def test_job_read_model_searches_snapshot_text() -> None:
    clock = FixedClock()
    jobs = InMemoryJobRepository()
    snapshots = InMemoryJobInputSnapshotRepository()
    queue = DefaultJobQueue(jobs=jobs, clock=clock, max_active_jobs_total=10)
    os_job = queue.submit_generation_job("project-os")
    bio_job = queue.submit_generation_job("project-bio")
    snapshots.save(
        JobInputSnapshot(
            job_id=os_job.id,
            project_id=os_job.project_id,
            script_text="[S1] Semaphore scheduling notes.",
            script_source=ScriptSource.PASTED,
            speakers=("S1",),
            chunks=(),
            voice_profile_id="default",
            tts_params={},
            created_at=clock.now(),
        )
    )
    snapshots.save(
        JobInputSnapshot(
            job_id=bio_job.id,
            project_id=bio_job.project_id,
            script_text="[S1] Cellular respiration.",
            script_source=ScriptSource.PASTED,
            speakers=("S1",),
            chunks=(),
            voice_profile_id="default",
            tts_params={},
            created_at=clock.now(),
        )
    )

    results = JobReadModel(jobs=jobs, snapshots=snapshots).list(q="semaphore")

    assert [result.job.id for result in results] == [os_job.id]
    assert results[0].snapshot is not None


def test_audio_read_model_resolves_project_latest_and_specific_job_audio(tmp_path) -> None:
    clock = FixedClock()
    jobs = InMemoryJobRepository()
    storage = LocalFileStorage(tmp_path / "storage")
    queue = DefaultJobQueue(jobs=jobs, clock=clock, max_active_jobs_total=10)
    first = queue.submit_generation_job("project-1")
    first.mark_running(clock.now())
    first.mark_completed(clock.now())
    jobs.save(first)
    second = queue.submit_generation_job("project-1")
    second.mark_running(clock.now())
    second.mark_completed(clock.now())
    jobs.save(second)
    first_path = storage.path_for_final_audio("project-1", first.id)
    second_path = storage.path_for_final_audio("project-1", second.id)
    first_path.parent.mkdir(parents=True, exist_ok=True)
    first_path.write_bytes(b"RIFFfirst")
    second_path.parent.mkdir(parents=True, exist_ok=True)
    second_path.write_bytes(b"RIFFsecond")

    read_model = AudioReadModel(jobs=jobs, storage=storage)

    assert read_model.latest_final_audio_path("project-1") == second_path
    assert read_model.job_final_audio_path(first.id) == first_path
