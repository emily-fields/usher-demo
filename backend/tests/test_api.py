import json

import pytest
from fastapi.testclient import TestClient

from app.api import Services
from app.jobs import DONE, JobStore
from app.main import create_app
from app.trees import TreeRegistry


class FakeRunner:
    def __init__(self):
        self.submitted = []

    def submit(self, job_id):
        self.submitted.append(job_id)

    def shutdown(self):
        pass


@pytest.fixture
def client(settings):
    tree_dir = settings.trees_dir / "rsv-a"
    (tree_dir / "examples").mkdir(parents=True)
    (tree_dir / "manifest.json").write_text(json.dumps({"leaf_count": 42}))
    (tree_dir / "examples" / "example.fasta").write_text(">NC_001803.1 OK1.1\nACGT\n")
    services = Services(settings, TreeRegistry(settings.trees_dir), JobStore(settings.jobs_dir), FakeRunner())
    with TestClient(create_app(settings, services)) as c:
        c.services = services
        yield c


def test_organisms(client):
    assert client.get("/api/organisms").json() == [
        {"key": "rsv-a", "organism": "RSV-A", "accession": "NC_001803.1", "leaf_count": 42, "has_example": True}
    ]


def test_create_job_queues_and_returns_id(client):
    files = {"fasta": ("in.fasta", b">NC_001803.1 s1\nACGT\n"), "metadata": ("m.tsv", b"sample\tdate\ns1\t2024\n")}
    response = client.post("/api/jobs", files=files)
    assert response.status_code == 202
    job_id = response.json()["id"]
    assert client.services.runner.submitted == [job_id]
    body = client.get(f"/api/jobs/{job_id}").json()
    assert (body["status"], body["organism"], body["metadata_columns"]) == ("queued", "RSV-A", ["date"])


def test_create_job_returns_all_errors(client):
    response = client.post("/api/jobs", files={"fasta": ("in.vcf", b"##fileformat=VCF\n")})
    assert response.status_code == 400
    assert "Only FASTA files" in response.json()["errors"][0]


@pytest.mark.parametrize("job_id", ["not-a-uuid", "..%2F..%2Fetc", "00000000-0000-0000-0000-000000000000"])
def test_unknown_jobs_404(client, job_id):
    assert client.get(f"/api/jobs/{job_id}").status_code == 404
    assert client.get(f"/api/jobs/{job_id}/tree").status_code == 404


def test_tree_409_until_done_then_served(client):
    job_id = client.post("/api/jobs", files={"fasta": ("in.fa", b">NC_001803.1 s1\nACGT\n")}).json()["id"]
    assert client.get(f"/api/jobs/{job_id}/tree").status_code == 409
    store = client.services.store
    job = store.get(job_id)
    job.status = DONE
    store.save(job)
    store.tree_path(job_id).write_bytes(b"gz")
    assert client.get(f"/api/jobs/{job_id}/tree").content == b"gz"


def test_example_files(client):
    assert client.get("/api/examples/rsv-a/fasta").text.startswith(">NC_001803.1")
    assert client.get("/api/examples/rsv-a/metadata").status_code == 404
    assert client.get("/api/examples/nope/fasta").status_code == 404
