import os
from dataclasses import dataclass
from pathlib import Path

# backend/app/config.py -> repo root (also /app inside the Docker image)
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    trees_dir: Path
    frontend_dist: Path
    job_workers: int = 2
    usher_threads: int = 4
    docker_wrap: bool = False
    usher_image: str = "efields236/soar-usher:latest"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"


def _path(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).resolve()


def load_settings() -> Settings:
    return Settings(
        data_dir=_path("DATA_DIR", REPO_ROOT / "data"),
        trees_dir=_path("TREES_DIR", REPO_ROOT / "trees"),
        frontend_dist=_path("FRONTEND_DIST", REPO_ROOT / "frontend" / "dist"),
        job_workers=int(os.getenv("JOB_WORKERS", "2")),
        usher_threads=int(os.getenv("USHER_THREADS", "4")),
        docker_wrap=os.getenv("DOCKER_WRAP", "false").lower() == "true",
        usher_image=os.getenv("USHER_IMAGE", "efields236/soar-usher:latest"),
    )
