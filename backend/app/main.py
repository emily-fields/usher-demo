import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.api import Services, router
from app.config import Settings, load_settings
from app.jobs import JobRunner, JobStore
from app.trees import TreeRegistry

logger = logging.getLogger(__name__)


def build_services(settings: Settings) -> Services:
    registry = TreeRegistry(settings.trees_dir)
    store = JobStore(settings.jobs_dir)
    return Services(settings, registry, store, JobRunner(store, registry, settings))


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    index = dist / "index.html"
    if not index.exists():
        logger.info("No built frontend at %s; serving API only", dist)
        return
    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        candidate = (root / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    settings = settings or load_settings()
    services = services or build_services(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        recovered = services.store.recover_interrupted()
        if recovered:
            logger.warning("Marked %d interrupted job(s) as failed", recovered)
        yield
        services.runner.shutdown()

    app = FastAPI(title="UShER Demo", lifespan=lifespan)
    app.state.services = services
    app.include_router(router)
    _mount_frontend(app, settings.frontend_dist)
    return app
