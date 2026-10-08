import time

import httpx

from app.trees import NCBI_EFETCH


def fetch_sequence(accession: str) -> str | None:
    """Return the nucleotide sequence for a GenBank accession, or None if NCBI has nothing."""
    time.sleep(0.4)  # NCBI allows 3 requests/second without an API key
    try:
        response = httpx.get(
            NCBI_EFETCH,
            params={"db": "nuccore", "id": accession, "rettype": "fasta", "retmode": "text"},
            timeout=60,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    lines = response.text.strip().splitlines()
    if not lines or not lines[0].startswith(">"):
        return None
    return "".join(line.strip() for line in lines[1:]).upper()
