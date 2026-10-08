import gzip
import re
from collections.abc import Collection
from dataclasses import dataclass

FASTA_EXTENSIONS = (".fa", ".fasta", ".fna")
INTERNAL_PREFIX = "upload_"
ACCESSION_ALIASES = {"OR957580.1": "NC_045512.2"}
SEQUENCE_RE = re.compile(r"^[ACGTURYSWKMBDHVN-]+$", re.IGNORECASE)
NAME_RE = re.compile(r"^[A-Za-z0-9._\-/|]+$")
HEADER_HINT = "Each header must look like '>ACCESSION sample_name'"


class ValidationError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class FastaRecord:
    name: str
    sequence: str

    @property
    def internal_name(self) -> str:
        return INTERNAL_PREFIX + self.name


@dataclass(frozen=True)
class ParsedFasta:
    accession: str
    records: list[FastaRecord]

    def to_internal_fasta(self) -> str:
        return "".join(f">{r.internal_name}\n{r.sequence}\n" for r in self.records)


def decode_upload(data: bytes) -> str:
    if data[:2] == b"\x1f\x8b":
        try:
            data = gzip.decompress(data)
        except (OSError, EOFError) as e:
            raise ValidationError(["File looks gzipped but could not be decompressed."]) from e
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValidationError(["File is not UTF-8 text."]) from e


def is_fasta_filename(filename: str) -> bool:
    return filename.lower().removesuffix(".gz").endswith(FASTA_EXTENSIONS)


def parse_fasta(filename: str, data: bytes, supported_accessions: Collection[str]) -> ParsedFasta:
    if not is_fasta_filename(filename):
        raise ValidationError([f"Only FASTA files are accepted (.fa, .fasta, .fna, optionally .gz); got '{filename}'."])
    lines = [line.strip() for line in decode_upload(data).splitlines()]
    lines = [line for line in lines if line]
    if not lines or not lines[0].startswith(">"):
        raise ValidationError(["This does not look like FASTA: the first line must start with '>'."])

    blocks: list[tuple[str, list[str]]] = []
    for line in lines:
        if line.startswith(">"):
            blocks.append((line[1:].strip(), []))
        else:
            blocks[-1][1].append(line)

    errors: list[str] = []
    records: list[FastaRecord] = []
    accessions: set[str] = set()
    seen: set[str] = set()
    for index, (header, seq_lines) in enumerate(blocks, start=1):
        tokens = header.split()
        if not tokens:
            errors.append(f"Record {index}: header is empty. {HEADER_HINT}.")
            continue
        accessions.add(ACCESSION_ALIASES.get(tokens[0], tokens[0]))
        name = tokens[1] if len(tokens) > 1 else f"sample_{index}"
        label = f"Record {index} ({name})"
        if not NAME_RE.match(name):
            errors.append(f"{label}: sample names may only contain letters, digits and . _ - / |. {HEADER_HINT}.")
        if name in seen:
            errors.append(f"{label}: duplicate sample name.")
        seen.add(name)
        sequence = "".join(seq_lines).upper()
        if not sequence:
            errors.append(f"{label}: sequence is empty.")
        elif not SEQUENCE_RE.match(sequence):
            errors.append(f"{label}: sequence contains characters that are not IUPAC nucleotide codes.")
        records.append(FastaRecord(name, sequence))

    supported = ", ".join(sorted(supported_accessions))
    if len(accessions) > 1:
        errors.append(
            f"All records must start with the same reference accession; found {', '.join(sorted(accessions))}. "
            f"{HEADER_HINT}, using one of: {supported}."
        )
    elif accessions and next(iter(accessions)) not in supported_accessions:
        errors.append(f"Reference accession {next(iter(accessions))} is not supported. {HEADER_HINT}, using one of: {supported}.")
    if errors:
        raise ValidationError(errors)
    return ParsedFasta(next(iter(accessions)), records)
