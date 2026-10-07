from pathlib import Path

from app.config import Settings
from app.pipeline.runner import run_tool

FATOVCF_TIMEOUT = 600


def to_vcf(aligned: Path, reference: Path, workdir: Path, settings: Settings, log_dir: Path) -> Path:
    # nextclade --output-fasta omits the reference; faToVcf needs it as the first record.
    combined = workdir / "aligned_with_reference.fasta"
    combined.write_text(reference.read_text().strip() + "\n" + aligned.read_text())
    out = workdir / "samples.vcf"
    run_tool(["faToVcf", combined, out], workdir=workdir, settings=settings,
             timeout=FATOVCF_TIMEOUT, log_path=log_dir / "faToVcf.log")
    return out
