import gzip
import json

import pytest

from app import jobs
from app.fasta import FastaRecord, ParsedFasta
from app.jobs import DONE, FAILED, JobRunner, JobStore
from app.metadata import UploadedMetadata, write_merged_metadata
from app.pipeline.runner import ToolError
from app.trees import TreeRegistry


@pytest.fixture
def registry(settings):
    tree_dir = settings.trees_dir / "rsv-a"
    tree_dir.mkdir(parents=True)
    (tree_dir / "manifest.json").write_text(json.dumps({"leaf_count": 2}))
    (tree_dir / "tree.pb.gz").write_bytes(b"pb")
    (tree_dir / "reference.fa").write_text(">ref\nACGT\n")
    (tree_dir / "metadata.tsv.gz").write_bytes(gzip.compress(b"strain\tdate\nA\t2020\n"))
    return TreeRegistry(settings.trees_dir)


def _parsed():
    return ParsedFasta("NC_001803.1", [FastaRecord("s1", "ACGT"), FastaRecord("s2", "ACGT")])


def _fake_tools(monkeypatch, aligned_names, placed_names, view_error=None):
    def fake_align(samples_fasta, reference, workdir, settings, log_dir):
        out = workdir / "aligned.fasta"
        out.write_text("".join(f">{n}\nACGT\n" for n in aligned_names))
        return out

    def fake_view(placed, metadata, columns, workdir, settings, log_dir):
        if view_error:
            raise view_error
        out = workdir / "tree.jsonl.gz"
        out.write_bytes(b"view")
        return out

    monkeypatch.setattr(jobs, "align", fake_align)
    monkeypatch.setattr(jobs, "to_vcf", lambda aligned, ref, workdir, s, log: workdir / "samples.vcf")
    monkeypatch.setattr(jobs, "place", lambda tree, vcf, workdir, s, log: workdir / "placed.pb")
    monkeypatch.setattr(jobs, "list_samples", lambda tree, workdir, s, log_path=None: {"A", *placed_names})
    monkeypatch.setattr(jobs, "build_view", fake_view)


def test_successful_job_marks_unplaced_samples(settings, registry, monkeypatch):
    _fake_tools(monkeypatch, aligned_names=["upload_s1", "upload_s2"], placed_names=["upload_s1"])
    store = JobStore(settings.jobs_dir)
    job = store.create(_parsed(), "RSV-A", UploadedMetadata(["date"], {"s1": {"date": "2024"}}))
    JobRunner(store, registry, settings).run(job.id)

    result = store.get(job.id)
    assert result.status == DONE, result.error
    assert [(s.name, s.placed, s.reason) for s in result.samples] == [
        ("s1", True, None),
        ("s2", False, "UShER could not place this sample"),
    ]
    assert store.tree_path(job.id).read_bytes() == b"view"
    assert set(result.step_timings) == {"aligning", "placing", "building_view"}


def test_job_fails_readably_when_nothing_aligns(settings, registry, monkeypatch):
    _fake_tools(monkeypatch, aligned_names=[], placed_names=[])
    store = JobStore(settings.jobs_dir)
    job = store.create(_parsed(), "RSV-A", None)
    JobRunner(store, registry, settings).run(job.id)

    result = store.get(job.id)
    assert result.status == FAILED
    assert result.failed_step == "aligning"
    assert "None of the samples could be aligned" in result.error


def test_tool_error_becomes_job_error(settings, registry, monkeypatch):
    _fake_tools(monkeypatch, ["upload_s1"], ["upload_s1"], view_error=ToolError("usher_to_taxonium", "boom"))
    store = JobStore(settings.jobs_dir)
    job = store.create(_parsed(), "RSV-A", None)
    JobRunner(store, registry, settings).run(job.id)
    result = store.get(job.id)
    assert (result.status, result.failed_step, result.error) == (FAILED, "building_view", "usher_to_taxonium failed: boom")


def test_recover_interrupted_marks_running_jobs_failed(settings):
    store = JobStore(settings.jobs_dir)
    job = store.create(_parsed(), "RSV-A", None)
    job.status = "placing"
    store.save(job)
    assert store.recover_interrupted() == 1
    assert store.get(job.id).error == "server restarted"


def test_merged_metadata_flattens_tabs_and_marks_uploads(tmp_path):
    base = tmp_path / "base.tsv.gz"
    base.write_bytes(gzip.compress(b"strain\tdate\nA\t2020\n"))
    uploaded = UploadedMetadata(["date", "lab"], {"s1": {"date": "2024", "lab": "a\tb"}})
    out = tmp_path / "merged.tsv"
    header = write_merged_metadata(base, uploaded, ["upload_s1", "upload_s2"], out)
    assert header == ["strain", "date", "lab", "placed_sample"]
    assert out.read_text().splitlines() == [
        "strain\tdate\tlab\tplaced_sample",
        "A\t2020\t\t",
        "upload_s1\t2024\ta b\tyes",
        "upload_s2\t\t\tyes",
    ]
