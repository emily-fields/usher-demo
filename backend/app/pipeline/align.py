from pathlib import Path

from app.config import Settings
from app.pipeline.runner import run_tool

NEXTCLADE_TIMEOUT = 600


def align(samples_fasta: Path, reference: Path, workdir: Path, settings: Settings, log_dir: Path) -> Path:
    out = workdir / "aligned.fasta"
    run_tool(
        ["nextclade", "run", "--input-ref", reference, "--output-fasta", out, samples_fasta],
        workdir=workdir, settings=settings, timeout=NEXTCLADE_TIMEOUT, log_path=log_dir / "nextclade.log",
    )
    if not out.exists():
        out.write_text("")
    return out


def fasta_names(path: Path) -> list[str]:
    return [line[1:].split()[0] for line in path.read_text().splitlines() if line.startswith(">") and line[1:].strip()]
