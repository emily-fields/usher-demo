import csv
import gzip
import io
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from app.fasta import INTERNAL_PREFIX, ValidationError, decode_upload

METADATA_EXTENSIONS = (".tsv", ".csv")
PLACED_COLUMN = "placed_sample"


@dataclass(frozen=True)
class UploadedMetadata:
    columns: list[str]
    rows: dict[str, dict[str, str]]

    def to_dict(self) -> dict:
        return {"columns": self.columns, "rows": self.rows}

    @classmethod
    def from_dict(cls, d: dict) -> "UploadedMetadata":
        return cls(columns=d["columns"], rows=d["rows"])


def parse_metadata(filename: str, data: bytes, sample_names: set[str]) -> UploadedMetadata:
    lower = filename.lower().removesuffix(".gz")
    if not lower.endswith(METADATA_EXTENSIONS):
        raise ValidationError([f"Metadata must be a .tsv or .csv file; got '{filename}'."])
    delimiter = "\t" if lower.endswith(".tsv") else ","
    table = [row for row in csv.reader(io.StringIO(decode_upload(data)), delimiter=delimiter)
             if any(cell.strip() for cell in row)]
    if not table:
        raise ValidationError(["Metadata file is empty."])

    header = [h.strip() for h in table[0]]
    errors: list[str] = []
    if len(header) < 2:
        raise ValidationError(["Metadata needs a sample-name column and at least one more column."])
    columns = header[1:]
    if any(not h for h in header):
        errors.append("Every metadata column needs a header.")
    if len(set(header)) != len(header):
        errors.append("Metadata has duplicate column names.")
    if PLACED_COLUMN in columns:
        errors.append(f"'{PLACED_COLUMN}' is a reserved column name.")
    if any(c in h for h in columns for c in ",\t\n\r"):
        errors.append("Metadata column names cannot contain commas, tabs or line breaks.")

    rows: dict[str, dict[str, str]] = {}
    for line_no, row in enumerate(table[1:], start=2):
        name = row[0].strip()
        if not name:
            errors.append(f"Line {line_no}: sample name is empty.")
            continue
        if len(row) > len(header):
            errors.append(f"Line {line_no} ({name}): has {len(row)} fields but the header has {len(header)}.")
        if name in rows:
            errors.append(f"Line {line_no}: duplicate sample '{name}'.")
            continue
        if name not in sample_names:
            errors.append(f"Line {line_no}: sample '{name}' is not in the FASTA file.")
        values = [cell.strip() for cell in row[1:]]
        values += [""] * (len(columns) - len(values))
        rows[name] = dict(zip(columns, values))
    if errors:
        raise ValidationError(errors)
    return UploadedMetadata(columns, rows)


def _open_text(path: Path):
    with path.open("rb") as f:
        gzipped = f.read(2) == b"\x1f\x8b"
    if gzipped:
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open(encoding="utf-8", newline="")


def _split(line: str) -> list[str]:
    return line.rstrip("\r\n").split("\t")


def choose_key_column(src: Path, names: set[str]) -> int:
    """Pick the column whose values are the tree's leaf names.

    viral_usher_trees metadata keys rows by `strain` while tree nodes are named by
    accession; in that case the `accession` column matches better (ported from soar's
    normalize_base_metadata_strains).
    """
    with _open_text(src) as f:
        header = _split(f.readline())
        if "accession" not in header:
            return 0
        acc = header.index("accession")
        first_hits = acc_hits = 0
        for line in f:
            cols = _split(line)
            first_hits += cols[0] in names
            acc_hits += acc < len(cols) and cols[acc] in names
    return acc if acc_hits > first_hits else 0


def iter_base_rows(src: Path, key_index: int) -> Iterator[list[str]]:
    """Yield the header, then each row re-keyed so column 0 is the leaf name."""
    with _open_text(src) as f:
        header = _split(f.readline())
        yield header if key_index == 0 else header + ["original_strain"]
        for line in f:
            if not line.strip():
                continue
            cols = _split(line)
            if key_index:
                key = cols[key_index] if key_index < len(cols) else ""
                cols = [key, *cols[1:], cols[0]]
            yield cols


def normalize_base_metadata(src: Path, keep: set[str], out: Path) -> int:
    rows = iter_base_rows(src, choose_key_column(src, keep))
    written = 0
    with gzip.open(out, "wt", encoding="utf-8", newline="") as w:
        w.write("\t".join(next(rows)) + "\n")
        for cols in rows:
            if cols[0] in keep:
                w.write("\t".join(cols) + "\n")
                written += 1
    return written


def _clean(value: str) -> str:
    return " ".join(value.replace("\t", " ").splitlines())


def write_merged_metadata(
    base: Path,
    uploaded: UploadedMetadata | None,
    placed_internal_names: list[str],
    out: Path,
) -> list[str]:
    rows = iter_base_rows(base, 0)
    base_header = next(rows)
    extra = [c for c in (uploaded.columns if uploaded else []) if c not in base_header]
    header = [*base_header, *extra, PLACED_COLUMN]
    width = len(header)
    with out.open("w", encoding="utf-8") as w:
        w.write("\t".join(header) + "\n")
        for cols in rows:
            cols = (cols + [""] * width)[: width - 1] + [""]
            w.write("\t".join(cols) + "\n")
        for internal in placed_internal_names:
            values = uploaded.rows.get(internal.removeprefix(INTERNAL_PREFIX), {}) if uploaded else {}
            cols = [internal, *(_clean(values.get(c, "")) for c in header[1:-1]), "yes"]
            w.write("\t".join(cols) + "\n")
    return header
