import json
import random
import re
import shutil
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.fasta import SEQUENCE_RE
from app.metadata import choose_key_column, iter_base_rows, normalize_base_metadata
from app.pipeline.matutils import list_samples, select
from app.prepare import ncbi
from app.prepare.download import download_file
from app.trees import TreeSpec

EXAMPLE_COLUMNS = ("date", "country", "pangolin_lineage", "Nextstrain_clade", "nextclade_clade", "clade", "lineage", "location", "host")
MAX_EXAMPLE_COLUMNS = 5
ACCESSION_LIKE = re.compile(r"^[A-Z]{1,2}_?\d{5,}\.\d+$")
CANDIDATE_POOL = 200


@dataclass(frozen=True)
class Example:
    name: str
    sequence: str
    metadata: dict[str, str]


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._\-/|]", "_", name)


def pick_examples(
    spec: TreeSpec,
    candidates: list[tuple[str, dict[str, str]]],
    reference_length: int,
    fetch: Callable[[str], str | None],
    count: int = 3,
) -> list[Example]:
    examples: list[Example] = []
    for name, row in candidates:
        accession = row.get(spec.example_accession_column, "").strip()
        if not accession and ACCESSION_LIKE.match(name):
            accession = name
        if not accession:
            continue
        sequence = fetch(accession)
        if not sequence or not SEQUENCE_RE.match(sequence) or len(sequence) < 0.9 * reference_length:
            continue
        metadata = {c: row[c] for c in EXAMPLE_COLUMNS if row.get(c, "").strip()}
        metadata = dict(list(metadata.items())[:MAX_EXAMPLE_COLUMNS])
        examples.append(Example(_safe_name(name), sequence, metadata))
        if len(examples) == count:
            break
    return examples


def _reference_length(path: Path) -> int:
    return sum(len(line.strip()) for line in path.read_text().splitlines() if not line.startswith(">"))


def _candidate_rows(metadata: Path, names: set[str], key_index: int) -> dict[str, dict[str, str]]:
    rows = iter_base_rows(metadata, key_index)
    header = next(rows)
    return {cols[0]: dict(zip(header, cols)) for cols in rows if cols[0] in names}


def _write_examples(spec: TreeSpec, examples: list[Example], directory: Path) -> None:
    directory.mkdir()
    (directory / "example.fasta").write_text(
        "".join(f">{spec.accession} {e.name}\n{e.sequence}\n" for e in examples)
    )
    columns = list(dict.fromkeys(c for e in examples for c in e.metadata))
    lines = ["\t".join(["sample", *columns])]
    lines += ["\t".join([e.name, *(e.metadata.get(c, "") for c in columns)]) for e in examples]
    (directory / "example-metadata.tsv").write_text("\n".join(lines) + "\n")


def prepare_tree(
    spec: TreeSpec,
    settings: Settings,
    size: int,
    download: Callable[[str, Path], None] = download_file,
    fetch: Callable[[str], str | None] = ncbi.fetch_sequence,
) -> Path:
    tmp = settings.trees_dir / ".tmp" / f"{spec.key}-{uuid.uuid4().hex[:8]}"
    tmp.mkdir(parents=True)
    try:
        download(spec.reference_url, tmp / "reference.fa")
        download(spec.tree_url, tmp / "full.pb.gz")
        download(spec.metadata_url, tmp / "full_metadata.tsv.gz")

        print("  listing full tree samples")
        full_samples = list_samples(tmp / "full.pb.gz", tmp, settings)
        if len(full_samples) > size:
            print(f"  pruning {len(full_samples)} -> {size}")
            keep = set(random.Random(spec.key).sample(sorted(full_samples), size))
            select(tmp / "full.pb.gz", keep, tmp / "tree.pb.gz", tmp, settings)
        else:
            shutil.copy(tmp / "full.pb.gz", tmp / "tree.pb.gz")
        kept = list_samples(tmp / "tree.pb.gz", tmp, settings)
        normalize_base_metadata(tmp / "full_metadata.tsv.gz", kept, tmp / "metadata.tsv.gz")

        print("  picking examples")
        pool = sorted(full_samples - kept)
        random.Random(spec.key).shuffle(pool)
        pool = pool[:CANDIDATE_POOL]
        key_index = choose_key_column(tmp / "full_metadata.tsv.gz", full_samples)
        rows = _candidate_rows(tmp / "full_metadata.tsv.gz", set(pool), key_index)
        candidates = [(name, rows[name]) for name in pool if name in rows]
        examples = pick_examples(spec, candidates, _reference_length(tmp / "reference.fa"), fetch)
        if examples:
            _write_examples(spec, examples, tmp / "examples")
        else:
            print("  WARNING: no examples found (tree may not have been pruned)")

        manifest = {
            "key": spec.key,
            "organism": spec.organism,
            "accession": spec.accession,
            "tree_url": spec.tree_url,
            "metadata_url": spec.metadata_url,
            "reference_url": spec.reference_url,
            "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "prune_size": size,
            "source_leaf_count": len(full_samples),
            "leaf_count": len(kept),
            "examples": [e.name for e in examples],
        }
        (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        for name in ("full.pb.gz", "full_metadata.tsv.gz", "prune.log", "keep.txt"):
            (tmp / name).unlink(missing_ok=True)

        final = settings.trees_dir / spec.key
        old = settings.trees_dir / ".tmp" / f"{spec.key}-old-{uuid.uuid4().hex[:8]}"
        if final.exists():
            final.rename(old)
        tmp.rename(final)
        shutil.rmtree(old, ignore_errors=True)
        return final
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
