from dataclasses import dataclass

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.config import Settings
from app.fasta import ValidationError, parse_fasta
from app.jobs import DONE, JobRunner, JobStore
from app.metadata import parse_metadata
from app.trees import TreeRegistry

router = APIRouter(prefix="/api")


@dataclass
class Services:
    settings: Settings
    registry: TreeRegistry
    store: JobStore
    runner: JobRunner


def _services(request: Request) -> Services:
    return request.app.state.services


@router.get("/organisms")
def organisms(request: Request) -> list[dict]:
    return [
        {
            "key": t.key,
            "organism": t.organism,
            "accession": t.accession,
            "leaf_count": t.leaf_count,
            "has_example": t.example_fasta_path.exists(),
        }
        for t in _services(request).registry.available()
    ]


@router.post("/jobs", status_code=202)
def create_job(request: Request, fasta: UploadFile = File(...), metadata: UploadFile | None = File(None)):
    services = _services(request)
    try:
        parsed = parse_fasta(fasta.filename or "", fasta.file.read(), services.registry.supported_accessions())
        uploaded = None
        if metadata is not None and metadata.filename:
            uploaded = parse_metadata(metadata.filename, metadata.file.read(), {r.name for r in parsed.records})
    except ValidationError as e:
        return JSONResponse({"errors": e.errors}, status_code=400)
    tree = services.registry.by_accession(parsed.accession)
    job = services.store.create(parsed, tree.organism, uploaded)
    services.runner.submit(job.id)
    return {"id": job.id}


@router.get("/jobs/{job_id}")
def get_job(request: Request, job_id: str) -> dict:
    job = _services(request).store.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job.to_dict()


@router.get("/jobs/{job_id}/tree")
def get_tree(request: Request, job_id: str):
    store = _services(request).store
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status != DONE:
        raise HTTPException(409, "Job is not finished")
    return FileResponse(store.tree_path(job.id), media_type="application/octet-stream",
                        filename="tree.jsonl.gz")


@router.get("/examples/{key}/{kind}")
def get_example(request: Request, key: str, kind: str):
    tree = _services(request).registry.by_key(key)
    paths = {"fasta": "example_fasta_path", "metadata": "example_metadata_path"}
    if tree is None or kind not in paths:
        raise HTTPException(404, "Example not found")
    path = getattr(tree, paths[kind])
    if not path.exists():
        raise HTTPException(404, "Example not found")
    return FileResponse(path, media_type="text/plain", filename=f"{key}-{path.name}")
