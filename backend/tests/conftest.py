import pytest

from app.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path / "data",
        trees_dir=tmp_path / "trees",
        frontend_dist=tmp_path / "dist",
        job_workers=1,
        usher_threads=1,
    )
