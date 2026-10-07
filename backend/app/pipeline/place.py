from pathlib import Path

from app.config import Settings
from app.pipeline.runner import ToolError, run_tool

USHER_TIMEOUT = 3600


def place(base_tree: Path, vcf: Path, workdir: Path, settings: Settings, log_dir: Path) -> Path:
    # Outputs go to the working directory (usher's default -d) and -o is passed by name:
    # matUtils hangs on absolute -o paths and usher's help doesn't say how it resolves them.
    out = workdir / "placed.pb"
    run_tool(
        ["usher", "-i", base_tree, "-v", vcf, "-u", "-T", str(settings.usher_threads), "-o", out.name],
        workdir=workdir, settings=settings, timeout=USHER_TIMEOUT, log_path=log_dir / "usher.log",
    )
    if not out.exists():
        raise ToolError("usher", "finished without writing a tree")
    return out
