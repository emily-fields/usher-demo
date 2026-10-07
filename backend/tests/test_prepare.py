import gzip

from app.metadata import normalize_base_metadata
from app.prepare.build import pick_examples
from app.trees import spec_by_key


def _gz(path, text):
    path.write_bytes(gzip.compress(text.encode()))
    return path


def test_normalize_keeps_only_leaves(tmp_path):
    src = _gz(tmp_path / "m.tsv.gz", "strain\tdate\nA\t2020\nB\t2021\nC\t2022\n")
    out = tmp_path / "out.tsv.gz"
    assert normalize_base_metadata(src, {"A", "C"}, out) == 2
    assert gzip.decompress(out.read_bytes()).decode() == "strain\tdate\nA\t2020\nC\t2022\n"


def test_normalize_rekeys_viral_usher_strains_by_accession(tmp_path):
    src = _gz(tmp_path / "m.tsv.gz", "strain\taccession\tdate\nhRSV/1\tOK1.1\t2020\nhRSV/2\tOK2.1\t2021\n")
    out = tmp_path / "out.tsv.gz"
    normalize_base_metadata(src, {"OK2.1"}, out)
    assert gzip.decompress(out.read_bytes()).decode() == (
        "strain\taccession\tdate\toriginal_strain\nOK2.1\tOK2.1\t2021\thRSV/2\n"
    )


def test_pick_examples_skips_bad_candidates():
    spec = spec_by_key("rsv-a")
    candidates = [
        ("no_acc", {"date": "2020"}),
        ("OK1.1", {"accession": "OK1.1", "date": "2021", "country": "USA"}),
        ("OK2.1", {"accession": "OK2.1", "date": "2022"}),
        ("OK3.1", {"accession": "OK3.1", "date": "2023"}),
    ]
    seqs = {"OK1.1": "ACGT" * 25, "OK2.1": "AC", "OK3.1": "ACGN" * 25}
    examples = pick_examples(spec, candidates, reference_length=100, fetch=seqs.get, count=2)
    assert [e.name for e in examples] == ["OK1.1", "OK3.1"]  # OK2.1 too short, no_acc has no accession
    assert examples[0].metadata == {"date": "2021", "country": "USA"}
