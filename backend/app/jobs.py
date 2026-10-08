import json
import logging
import os
import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.fasta import INTERNAL_PREFIX, ParsedFasta
from app.metadata import UploadedMetadata, write_merged_metadata
from app.pipeline.align import align, fasta_names
from app.pipeline.matutils import list_samples
from app.pipeline.place import place
from app.pipeline.runner import ToolError
from app.pipeline.taxonium import build_view
from app.pipeline.vcf import to_vcf
from app.trees import TreeRegistry

logger = logging.getLogger(__name__)

QUEUED = "queued"
ALIGNING = "aligning"
PLACING = "placing"
BUILDING_VIEW = "building_view"
DONE = "done"
FAILED = "failed"
ACTIVE_STATUSES = {QUEUED, ALIGNING, PLACING, BUILDING_VIEW}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class PipelineError(Exception):
    """A failure with a message that is already readable by a demo audience."""


@dataclass
class SampleResult:
    name: str
    placed: bool | None = None
    reason: str | None = None


@dataclass
class Job:
    id: str
    status: str
    accession: str
    organism: str
    samples: list[SampleResult]
    metadata_columns: list[str]
    created_at: str
    step_started_at: str | None = None
    step_timings: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    failed_step: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        return cls(**{**d, "samples": [SampleResult(**s) for s in d["samples"]]})


class JobStore:
    def __init__(self, jobs_dir: Path):
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def tree_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "tree.jsonl.gz"

    def create(self, parsed: ParsedFasta, organism: str, metadata: UploadedMetadata | None) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            status=QUEUED,
            accession=parsed.accession,
            organism=organism,
            samples=[SampleResult(r.name) for r in parsed.records],
            metadata_columns=metadata.columns if metadata else [],
            created_at=_now(),
        )
        directory = self.job_dir(job.id)
        directory.mkdir(parents=True)
        (directory / "input.fasta").write_text(parsed.to_internal_fasta())
        if metadata:
            (directory / "metadata.json").write_text(json.dumps(metadata.to_dict()))
        self.save(job)
        return job

    def get(self, job_id: str) -> Job | None:
        try:
            job_id = str(uuid.UUID(job_id))
        except ValueError:
            return None
        path = self.job_dir(job_id) / "job.json"
        if not path.exists():
            return None
        return Job.from_dict(json.loads(path.read_text()))

    def save(self, job: Job) -> None:
        path = self.job_dir(job.id) / "job.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(job.to_dict(), indent=2))
        os.replace(tmp, path)

    def load_metadata(self, job_id: str) -> UploadedMetadata | None:
        path = self.job_dir(job_id) / "metadata.json"
        return UploadedMetadata.from_dict(json.loads(path.read_text())) if path.exists() else None

    def recover_interrupted(self) -> int:
        count = 0
        for path in self.jobs_dir.glob("*/job.json"):
            job = Job.from_dict(json.loads(path.read_text()))
            if job.status in ACTIVE_STATUSES:
                job.failed_step = job.status
                job.status = FAILED
                job.error = "server restarted"
                self.save(job)
                count += 1
        return count


class JobRunner:
    def __init__(self, store: JobStore, registry: TreeRegistry, settings: Settings):
        self.store = store
        self.registry = registry
        self.settings = settings
        self._executor = ThreadPoolExecutor(max_workers=settings.job_workers, thread_name_prefix="job")

    def submit(self, job_id: str) -> None:
        self._executor.submit(self.run, job_id)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def run(self, job_id: str) -> None:
        job = self.store.get(job_id)
        if job is None:
            return
        try:
            self._run_pipeline(job)
        except (ToolError, PipelineError) as e:
            self._fail(job, str(e))
        except Exception as e:
            logger.exception("Job %s crashed", job.id)
            self._fail(job, f"Unexpected error: {e}")

    def _fail(self, job: Job, message: str) -> None:
        job.failed_step = job.status
        job.status = FAILED
        job.error = message
        self.store.save(job)

    @contextmanager
    def _step(self, job: Job, status: str):
        job.status = status
        job.step_started_at = _now()
        self.store.save(job)
        started = time.monotonic()
        yield
        job.step_timings[status] = round(time.monotonic() - started, 1)
        self.store.save(job)

    def _run_pipeline(self, job: Job) -> None:
        tree = self.registry.by_accession(job.accession)
        if tree is None:
            raise PipelineError(f"No prepared tree for {job.accession}.")
        directory = self.store.job_dir(job.id)
        work = directory / "work"
        logs = directory / "logs"
        work.mkdir(exist_ok=True)
        logs.mkdir(exist_ok=True)

        with self._step(job, ALIGNING):
            aligned = align(directory / "input.fasta", tree.reference_path, work, self.settings, logs)
            aligned_names = set(fasta_names(aligned))
            for sample in job.samples:
                if INTERNAL_PREFIX + sample.name not in aligned_names:
                    sample.placed = False
                    sample.reason = "Could not be aligned to the reference"
            if not aligned_names:
                raise PipelineError(f"None of the samples could be aligned to the {job.organism} reference.")
            vcf = to_vcf(aligned, tree.reference_path, work, self.settings, logs)

        with self._step(job, PLACING):
            placed_tree = place(tree.tree_path, vcf, work, self.settings, logs)
            in_tree = list_samples(placed_tree, work, self.settings, log_path=logs / "matUtils.log")
            for sample in job.samples:
                if sample.placed is None:
                    sample.placed = INTERNAL_PREFIX + sample.name in in_tree
                    if not sample.placed:
                        sample.reason = "UShER could not place this sample"
            placed = [INTERNAL_PREFIX + s.name for s in job.samples if s.placed]
            if not placed:
                raise PipelineError("None of the samples could be placed on the tree.")

        with self._step(job, BUILDING_VIEW):
            merged = work / "metadata.tsv"
            columns = write_merged_metadata(tree.metadata_path, self.store.load_metadata(job.id), placed, merged)
            view = build_view(placed_tree, merged, columns, work, self.settings, logs)
            shutil.move(view, self.store.tree_path(job.id))

        job.status = DONE
        job.step_started_at = None
        self.store.save(job)
        shutil.rmtree(work, ignore_errors=True)
