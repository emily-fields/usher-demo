import uuid
from pathlib import Path

from app.config import Settings
from app.pipeline.runner import run_tool

MATUTILS_TIMEOUT = 3 * 3600


def list_samples(tree: Path, workdir: Path, settings: Settings, log_path: Path | None = None) -> set[str]:
    name = f"samples-{uuid.uuid4().hex[:8]}.txt"
    run_tool(["matUtils", "extract", "-i", tree, "-u", name],
             workdir=workdir, settings=settings, timeout=MATUTILS_TIMEOUT, log_path=log_path)
    path = workdir / name
    names = {line.strip() for line in path.read_text().splitlines() if line.strip()}
    path.unlink()
    return names


def select(tree: Path, names: set[str], output: Path, workdir: Path, settings: Settings) -> None:
    """Write a tree containing exactly `names` (`-z` keeps fewer samples than asked).

    matUtils resolves `-o` relative to its output directory and hangs when given an absolute
    path, so `output` must be inside `workdir` and is passed by name.
    """
    names_file = workdir / "keep.txt"
    names_file.write_text("\n".join(sorted(names)) + "\n")
    run_tool(["matUtils", "extract", "-i", tree, "-s", names_file.name, "-o", output.relative_to(workdir)],
             workdir=workdir, settings=settings, timeout=MATUTILS_TIMEOUT, log_path=workdir / "prune.log")
