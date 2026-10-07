import logging
from pathlib import Path

from app.config import Settings
from app.pipeline.runner import ToolError, run_tool

logger = logging.getLogger(__name__)

TAXONIUM_TIMEOUT = 3600
CHRONUMENTAL_STEPS = 100
DATE_COLUMN = "date"


def _command(placed: Path, metadata: Path, columns: list[str], out: Path, chronumental: bool) -> list:
    cmd = ["usher_to_taxonium", "--input", placed, "--output", out,
           "--metadata", metadata, "--columns", ",".join(columns)]
    if chronumental:
        cmd += ["--chronumental", "--chronumental_steps", str(CHRONUMENTAL_STEPS)]
    return cmd


def build_view(placed: Path, metadata: Path, columns: list[str], workdir: Path, settings: Settings, log_dir: Path) -> Path:
    out = workdir / "tree.jsonl.gz"
    if DATE_COLUMN in columns:
        try:
            run_tool(_command(placed, metadata, columns, out, True), workdir=workdir, settings=settings,
                     timeout=TAXONIUM_TIMEOUT, log_path=log_dir / "taxonium-chronumental.log")
            return out
        except ToolError:
            logger.warning("Chronumental failed, retrying without time tree", exc_info=True)
    run_tool(_command(placed, metadata, columns, out, False), workdir=workdir, settings=settings,
             timeout=TAXONIUM_TIMEOUT, log_path=log_dir / "taxonium.log")
    return out
