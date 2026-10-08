import gzip

import pytest

from app.fasta import ValidationError, parse_fasta
from app.metadata import parse_metadata

SUPPORTED = {"NC_045512.2", "NC_001803.1"}


def test_parses_multi_record_fasta_with_crlf_and_lowercase():
    data = b">NC_045512.2 s1 extra words\r\nacgt\r\nACGN\r\n>NC_045512.2\r\nAC-GT\r\n"
    parsed = parse_fasta("in.fasta", data, SUPPORTED)
    assert parsed.accession == "NC_045512.2"
    assert [(r.name, r.sequence) for r in parsed.records] == [("s1", "ACGTACGN"), ("sample_2", "AC-GT")]
    assert parsed.to_internal_fasta() == ">upload_s1\nACGTACGN\n>upload_sample_2\nAC-GT\n"


def test_accepts_gzipped_fasta_and_alias():
    parsed = parse_fasta("in.fa.gz", gzip.compress(b">OR957580.1 a\nACGT\n"), SUPPORTED)
    assert parsed.accession == "NC_045512.2"


@pytest.mark.parametrize(
    "filename,data,message",
    [
        ("in.vcf", b"##fileformat=VCFv4.2\n", "Only FASTA files"),
        ("in.fasta", b"ACGT\n", "must start with '>'"),
        ("in.fasta", b">NC_045512.2 a\n\n>NC_045512.2 b\nACGT\n", "(a): sequence is empty"),
        ("in.fasta", b">NC_045512.2 a\nACGTX\n", "not IUPAC"),
        ("in.fasta", b">NC_045512.2 a\nAC\n>NC_045512.2 a\nAC\n", "duplicate sample name"),
        ("in.fasta", b">NC_999999.1 a\nAC\n", "not supported"),
    ],
)
def test_rejects_bad_fasta(filename, data, message):
    with pytest.raises(ValidationError) as exc:
        parse_fasta(filename, data, SUPPORTED)
    assert any(message in e for e in exc.value.errors), exc.value.errors


def test_soar_style_headers_explain_expected_format():
    data = b">NC_045512.2 soar_id=SOAR_1\nACGT\n>soar_id=SOAR_2\nACGT\n"
    with pytest.raises(ValidationError) as exc:
        parse_fasta("in.fasta", data, SUPPORTED)
    assert any(">ACCESSION sample_name" in e for e in exc.value.errors)


def test_parses_csv_metadata_with_bom_and_quotes():
    data = '﻿sample,date,note\ns1,2024-01-02,"has, comma"\n'.encode()
    meta = parse_metadata("m.csv", data, {"s1", "s2"})
    assert meta.columns == ["date", "note"]
    assert meta.rows == {"s1": {"date": "2024-01-02", "note": "has, comma"}}


@pytest.mark.parametrize(
    "data,message",
    [
        (b"sample\n", "at least one"),
        (b"sample\tdate\nzzz\t2024\n", "not in the FASTA"),
        (b"sample\tdate\ns1\t1\ns1\t2\n", "duplicate"),
        (b"sample\tplaced_sample\ns1\tx\n", "reserved"),
    ],
)
def test_rejects_bad_metadata(data, message):
    with pytest.raises(ValidationError) as exc:
        parse_metadata("m.tsv", data, {"s1"})
    assert any(message in e for e in exc.value.errors), exc.value.errors


@pytest.mark.parametrize("header", [b'sample,"Location, city"\ns1,LA\n', b'sample,"a\tb"\ns1,LA\n'])
def test_rejects_metadata_column_names_that_break_taxonium(header):
    with pytest.raises(ValidationError) as exc:
        parse_metadata("m.csv", header, {"s1"})
    assert any("column names cannot contain" in e for e in exc.value.errors), exc.value.errors


@pytest.mark.parametrize("data", [b">NC_001803.1 soar_id=Y\nACGT\n", b">soar_id=Y\nACGT\n"])
def test_single_soar_style_header_explains_expected_format(data):
    with pytest.raises(ValidationError) as exc:
        parse_fasta("in.fasta", data, SUPPORTED)
    assert any(">ACCESSION sample_name" in e for e in exc.value.errors), exc.value.errors
