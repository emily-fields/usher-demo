import pytest

from app.config import load_settings
from app.fasta import parse_fasta
from app.jobs import DONE
from app.main import build_services
from app.metadata import parse_metadata
from app.trees import TreeRegistry

pytestmark = pytest.mark.integration

TREES = TreeRegistry(load_settings().trees_dir).available()


@pytest.mark.parametrize("tree", [t for t in TREES if t.example_fasta_path.exists()], ids=lambda t: t.key)
def test_example_places_end_to_end(tree):
    services = build_services(load_settings())
    parsed = parse_fasta("example.fasta", tree.example_fasta_path.read_bytes(), services.registry.supported_accessions())
    metadata = parse_metadata("example.tsv", tree.example_metadata_path.read_bytes(), {r.name for r in parsed.records})
    job = services.store.create(parsed, tree.organism, metadata)
    services.runner.run(job.id)
    result = services.store.get(job.id)
    assert result.status == DONE, result.error
    assert any(s.placed for s in result.samples)
    assert services.store.tree_path(job.id).stat().st_size > 0
