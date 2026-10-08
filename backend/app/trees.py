import json
from dataclasses import dataclass
from pathlib import Path

UCSC_BASE = "https://hgwdev.gi.ucsc.edu/~angie/UShER_SARS-CoV-2"
VIRAL_USHER_RAW_BASE = "https://raw.githubusercontent.com/AngieHinrichs/viral_usher_trees/main/trees"
NCBI_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


@dataclass(frozen=True)
class TreeSpec:
    key: str
    organism: str
    accession: str
    tree_url: str
    metadata_url: str
    reference_url: str
    example_accession_column: str


def _viral_usher(key: str, organism: str, accession: str, folder: str) -> TreeSpec:
    base = f"{VIRAL_USHER_RAW_BASE}/{folder}"
    return TreeSpec(
        key=key,
        organism=organism,
        accession=accession,
        tree_url=f"{base}/optimized.pb.gz",
        metadata_url=f"{base}/metadata.tsv.gz",
        reference_url=f"{base}/treetime_rerooted_{accession}.fa",
        example_accession_column="accession",
    )


TREE_SPECS: tuple[TreeSpec, ...] = (
    TreeSpec(
        key="sars-cov-2",
        organism="SARS-CoV-2",
        accession="NC_045512.2",
        tree_url=f"{UCSC_BASE}/public-latest.all.masked.ShUShER.pb.gz",
        metadata_url=f"{UCSC_BASE}/public-latest.metadata.tsv.gz",
        reference_url=f"{NCBI_EFETCH}?db=nuccore&id=NC_045512.2&rettype=fasta&retmode=text",
        example_accession_column="genbank_accession",
    ),
    _viral_usher("rsv-a", "RSV-A", "NC_001803.1", "Human_respiratory_syncytial_virus_A"),
    _viral_usher("rsv-b", "RSV-B", "NC_001781.1", "Human_orthopneumovirus_B1"),
    _viral_usher("flu-h3n2-ha", "Influenza A H3N2 (HA)", "NC_007366.1",
                 "Influenza_A_virus_A_New_York_392_2004_H3N2_4"),
)


def spec_by_key(key: str) -> TreeSpec:
    for spec in TREE_SPECS:
        if spec.key == key:
            return spec
    raise KeyError(key)


@dataclass(frozen=True)
class PreparedTree:
    key: str
    organism: str
    accession: str
    directory: Path
    leaf_count: int

    @property
    def tree_path(self) -> Path:
        return self.directory / "tree.pb.gz"

    @property
    def metadata_path(self) -> Path:
        return self.directory / "metadata.tsv.gz"

    @property
    def reference_path(self) -> Path:
        return self.directory / "reference.fa"

    @property
    def example_fasta_path(self) -> Path:
        return self.directory / "examples" / "example.fasta"

    @property
    def example_metadata_path(self) -> Path:
        return self.directory / "examples" / "example-metadata.tsv"


class TreeRegistry:
    def __init__(self, trees_dir: Path):
        self.trees_dir = trees_dir

    def available(self) -> list[PreparedTree]:
        trees = []
        for spec in TREE_SPECS:
            manifest_path = self.trees_dir / spec.key / "manifest.json"
            if not manifest_path.exists():
                continue
            manifest = json.loads(manifest_path.read_text())
            trees.append(PreparedTree(spec.key, spec.organism, spec.accession,
                                      manifest_path.parent, manifest["leaf_count"]))
        return trees

    def by_accession(self, accession: str) -> PreparedTree | None:
        return next((t for t in self.available() if t.accession == accession), None)

    def by_key(self, key: str) -> PreparedTree | None:
        return next((t for t in self.available() if t.key == key), None)

    def supported_accessions(self) -> list[str]:
        return [t.accession for t in self.available()]
