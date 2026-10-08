# usher-demo

Upload a FASTA file and watch UShER place the samples onto a pre-pruned phylogenetic tree, shown in Taxonium. No logins.

Trees (pruned to 10,000 samples, committed under `trees/`):

| Organism | Header accession | Status |
|---|---|---|
| RSV-A | `NC_001803.1` | built |
| RSV-B | `NC_001781.1` | built |
| Influenza A H3N2 (HA) | `NC_007366.1` | built |
| SARS-CoV-2 | `NC_045512.2` | not built yet (needs a machine with more than ~8 GB free for Docker; see below) |

FASTA headers look like `>NC_001803.1 my_sample`. Metadata (optional) is a TSV/CSV whose first column is the sample name. The app only offers trees that exist under `trees/`.

## Run with Docker

```bash
docker compose up --build
```
Open http://localhost:8000.

## Run for development (macOS)

Docker Desktop must be running; the bioinformatics tools run in the `efields236/soar-usher` image. The frontend needs Node 24 (`frontend/.nvmrc`).

```bash
cd backend && DOCKER_WRAP=true uv run uvicorn app.main:create_app --factory --reload
cd frontend && nvm use && npm install && npm run dev   # http://localhost:5173
```

## Tests

```bash
cd backend && uv run pytest                                   # fast tests
cd backend && DOCKER_WRAP=true uv run pytest -m integration   # real pipeline on each example
cd frontend && npx vitest run
```

## Rebuilding trees

```bash
cd backend && DOCKER_WRAP=true uv run python -m app.prepare             # all trees
cd backend && DOCKER_WRAP=true uv run python -m app.prepare sars-cov-2 --size 5000
```
Run without `DOCKER_WRAP` inside the image instead: `docker compose run --rm -v ./trees:/app/trees backend python -m app.prepare sars-cov-2` (the `-v` writes the result back into the repo's `trees/`).

The SARS-CoV-2 tree comes from UCSC's daily public build (millions of samples); loading it takes about 7.3 GB and pruning needs more, so Docker needs well over 8 GB of memory. Each rebuild is a new snapshot (see `trees/<key>/manifest.json`). Examples are real sequences that were pruned out of the tree, fetched from NCBI.
