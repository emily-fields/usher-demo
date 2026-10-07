import csv
import io
from dataclasses import dataclass

from app.fasta import ValidationError, decode_upload

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
