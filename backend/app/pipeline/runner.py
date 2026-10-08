import logging
import shlex
import subprocess
from pathlib import Path

from app.config import Settings

logger = logging.getLogger(__name__)

# Tools that only exist inside the soar-usher image. usher_to_taxonium is a Python
# package in our own environment, so it is never wrapped.
WRAPPED_TOOLS = frozenset({"usher", "matUtils", "faToVcf", "nextclade"})


class ToolError(RuntimeError):
    def __init__(self, tool: str, detail: str):
        super().__init__(f"{tool} failed: {detail}")
        self.tool = tool


def build_command(cmd: list[str], workdir: Path, settings: Settings) -> list[str]:
    if not (settings.docker_wrap and cmd[0] in WRAPPED_TOOLS):
        return list(cmd)
    wrapped = ["docker", "run", "--rm", "--platform", "linux/amd64"]
    mounts: list[str] = []
    for path in (settings.data_dir, settings.trees_dir, workdir):
        if str(path) not in mounts:
            mounts.append(str(path))
    for mount in mounts:
        wrapped += ["-v", f"{mount}:{mount}"]
    return wrapped + ["-w", str(workdir), settings.usher_image, *cmd]


def _write_log(log_path: Path | None, cmd: list[str], stdout: str, stderr: str) -> None:
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(f"$ {shlex.join(cmd)}\n\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n")


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def run_tool(
    cmd: list[str | Path],
    *,
    workdir: Path,
    settings: Settings,
    timeout: int,
    log_path: Path | None = None,
) -> str:
    args = [str(c) for c in cmd]
    full = build_command(args, workdir, settings)
    workdir.mkdir(parents=True, exist_ok=True)
    logger.info("Running %s", shlex.join(full))
    try:
        proc = subprocess.run(full, cwd=workdir, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise ToolError(args[0], f"timed out after {timeout}s") from e
    except FileNotFoundError as e:
        raise ToolError(args[0], "command not found (set DOCKER_WRAP=true or run inside the Docker image)") from e
    _write_log(log_path, full, proc.stdout, proc.stderr)
    if proc.returncode == 137:
        raise ToolError(args[0], "ran out of memory (killed); give Docker more memory")
    if proc.returncode != 0:
        raise ToolError(args[0], _last_line(proc.stderr) or f"exit code {proc.returncode}")
    return proc.stdout
