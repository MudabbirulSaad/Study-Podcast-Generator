from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from study_podcast.domain.entities import ActivePodcastScript, GenerationJob, StudyProject
from study_podcast.domain.value_objects import JobPhase, JobStatus, ScriptSource


class SQLiteStore:
    def __init__(self, database_path: Path | str) -> None:
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(database_path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._migrate()

    def save_active_script(self, script: ActivePodcastScript) -> None:
        self._connection.execute(
            """
            INSERT INTO scripts(project_id, text, source, speakers, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
              text=excluded.text,
              source=excluded.source,
              speakers=excluded.speakers,
              updated_at=excluded.updated_at
            """,
            (
                script.project_id,
                script.text,
                script.source.value,
                ",".join(script.speakers),
                script.updated_at.isoformat(),
            ),
        )
        self._connection.commit()

    def get_active_script(self, project_id: str) -> ActivePodcastScript | None:
        row = self._connection.execute(
            "SELECT * FROM scripts WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        if row is None:
            return None
        return ActivePodcastScript(
            project_id=row["project_id"],
            text=row["text"],
            source=ScriptSource(row["source"]),
            speakers=tuple(filter(None, row["speakers"].split(","))),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def save_project(self, project: StudyProject) -> None:
        self._connection.execute(
            """
            INSERT INTO projects(id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET title=excluded.title, updated_at=excluded.updated_at
            """,
            (
                project.id,
                project.title,
                project.created_at.isoformat(),
                project.updated_at.isoformat(),
            ),
        )
        self._connection.commit()

    def get_project(self, project_id: str) -> StudyProject | None:
        row = self._connection.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        return self._project_from_row(row) if row is not None else None

    def list_projects(self) -> list[StudyProject]:
        rows = self._connection.execute("SELECT * FROM projects ORDER BY created_at").fetchall()
        return [self._project_from_row(row) for row in rows]

    def save_job(self, job: GenerationJob) -> None:
        self._connection.execute(
            """
            INSERT INTO jobs(
              id, project_id, status, phase, progress_percent, total_chunks, completed_chunks,
              current_chunk_index, current_chunk_preview, message, failure_reason,
              cancellation_requested, created_at, started_at, updated_at, completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              status=excluded.status,
              phase=excluded.phase,
              progress_percent=excluded.progress_percent,
              total_chunks=excluded.total_chunks,
              completed_chunks=excluded.completed_chunks,
              current_chunk_index=excluded.current_chunk_index,
              current_chunk_preview=excluded.current_chunk_preview,
              message=excluded.message,
              failure_reason=excluded.failure_reason,
              cancellation_requested=excluded.cancellation_requested,
              started_at=excluded.started_at,
              updated_at=excluded.updated_at,
              completed_at=excluded.completed_at
            """,
            (
                job.id,
                job.project_id,
                job.status.value,
                job.phase.value,
                job.progress_percent,
                job.total_chunks,
                job.completed_chunks,
                job.current_chunk_index,
                job.current_chunk_preview,
                job.message,
                job.failure_reason,
                int(job.cancellation_requested),
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.updated_at.isoformat(),
                job.completed_at.isoformat() if job.completed_at else None,
            ),
        )
        self._connection.commit()

    def get_job(self, job_id: str) -> GenerationJob | None:
        row = self._connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._job_from_row(row) if row is not None else None

    def list_jobs(self) -> list[GenerationJob]:
        rows = self._connection.execute("SELECT * FROM jobs ORDER BY created_at").fetchall()
        return [self._job_from_row(row) for row in rows]

    def find_active_job_for_project(self, project_id: str) -> GenerationJob | None:
        row = self._connection.execute(
            """
            SELECT * FROM jobs
            WHERE project_id = ? AND status IN ('queued', 'running', 'cancel_requested')
            ORDER BY created_at
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
        return self._job_from_row(row) if row is not None else None

    def list_unfinished_jobs(self) -> list[GenerationJob]:
        rows = self._connection.execute(
            "SELECT * FROM jobs WHERE status IN ('queued', 'running', 'cancel_requested')"
        ).fetchall()
        return [self._job_from_row(row) for row in rows]

    def _project_from_row(self, row: sqlite3.Row) -> StudyProject:
        return StudyProject(
            id=row["id"],
            title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _job_from_row(self, row: sqlite3.Row) -> GenerationJob:
        return GenerationJob(
            id=row["id"],
            project_id=row["project_id"],
            status=JobStatus(row["status"]),
            phase=JobPhase(row["phase"]),
            progress_percent=row["progress_percent"],
            total_chunks=row["total_chunks"],
            completed_chunks=row["completed_chunks"],
            current_chunk_index=row["current_chunk_index"],
            current_chunk_preview=row["current_chunk_preview"],
            message=row["message"],
            failure_reason=row["failure_reason"],
            cancellation_requested=bool(row["cancellation_requested"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
        )

    def _migrate(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scripts (
              project_id TEXT PRIMARY KEY,
              text TEXT NOT NULL,
              source TEXT NOT NULL,
              speakers TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL,
              status TEXT NOT NULL,
              phase TEXT NOT NULL,
              progress_percent INTEGER NOT NULL,
              total_chunks INTEGER NOT NULL,
              completed_chunks INTEGER NOT NULL,
              current_chunk_index INTEGER,
              current_chunk_preview TEXT,
              message TEXT NOT NULL,
              failure_reason TEXT,
              cancellation_requested INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              started_at TEXT,
              updated_at TEXT NOT NULL,
              completed_at TEXT
            );
            """
        )
        self._connection.commit()


class SQLiteProjectRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, project: StudyProject) -> None:
        self.store.save_project(project)

    def get(self, project_id: str) -> StudyProject | None:
        return self.store.get_project(project_id)

    def list(self) -> list[StudyProject]:
        return self.store.list_projects()


class SQLiteScriptRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save_active(self, script: ActivePodcastScript) -> None:
        self.store.save_active_script(script)

    def get_active(self, project_id: str) -> ActivePodcastScript | None:
        return self.store.get_active_script(project_id)


class SQLiteJobRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, job: GenerationJob) -> None:
        self.store.save_job(job)

    def get(self, job_id: str) -> GenerationJob | None:
        return self.store.get_job(job_id)

    def list(self) -> list[GenerationJob]:
        return self.store.list_jobs()

    def find_active_for_project(self, project_id: str) -> GenerationJob | None:
        return self.store.find_active_job_for_project(project_id)

    def list_unfinished(self) -> list[GenerationJob]:
        return self.store.list_unfinished_jobs()
