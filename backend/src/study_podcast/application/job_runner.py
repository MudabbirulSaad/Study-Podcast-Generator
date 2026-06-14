from dataclasses import dataclass

from study_podcast.application.use_cases import Clock
from study_podcast.domain.entities import GenerationJob
from study_podcast.domain.errors import DomainError
from study_podcast.domain.ports import (
    AudioMerger,
    FileStorage,
    JobRepository,
    ProgressReporter,
    ScriptRepository,
    TtsEngine,
)
from study_podcast.domain.services import split_script_into_chunks
from study_podcast.domain.value_objects import JobStatus


@dataclass
class GenerationJobRunner:
    scripts: ScriptRepository
    jobs: JobRepository
    tts: TtsEngine
    merger: AudioMerger
    storage: FileStorage
    progress: ProgressReporter
    clock: Clock
    max_chunk_chars: int
    max_chunks: int

    def run(self, job_id: str) -> GenerationJob:
        job = self.jobs.get(job_id)
        if job is None:
            raise DomainError("job not found")
        if job.status is not JobStatus.QUEUED:
            return job

        try:
            job.mark_running(self.clock.now())
            self.progress.save(job)
            script = self.scripts.get_active(job.project_id)
            if script is None:
                raise DomainError("script not found")

            chunks = split_script_into_chunks(
                script.text,
                max_chunk_chars=self.max_chunk_chars,
                max_chunks=self.max_chunks,
            )
            job.set_chunking(total_chunks=len(chunks), now=self.clock.now())
            self.progress.save(job)

            audio_chunks = []
            for chunk in chunks:
                latest = self.jobs.get(job.id) or job
                if latest.cancellation_requested:
                    latest.mark_cancelled(self.clock.now())
                    self.progress.save(latest)
                    return latest
                output_path = self.storage.path_for_chunk(job.project_id, job.id, chunk.index)
                audio = self.tts.synthesize(chunk=chunk, output_path=output_path)
                audio_chunks.append(audio)
                job.record_chunk_progress(
                    completed_chunks=len(audio_chunks),
                    current_chunk_index=chunk.index,
                    current_chunk_preview=chunk.text,
                    now=self.clock.now(),
                )
                self.progress.save(job)

            latest = self.jobs.get(job.id) or job
            if latest.cancellation_requested:
                latest.mark_cancelled(self.clock.now())
                self.progress.save(latest)
                return latest

            job.mark_merging(self.clock.now())
            self.progress.save(job)
            self.merger.merge(
                chunks=audio_chunks,
                output_path=self.storage.path_for_final_audio(job.project_id, job.id),
            )
            job.mark_finalizing(self.clock.now())
            self.progress.save(job)
            job.mark_completed(self.clock.now())
            self.progress.save(job)
            return job
        except Exception as exc:
            job.mark_failed(str(exc), self.clock.now())
            self.progress.save(job)
            return job
