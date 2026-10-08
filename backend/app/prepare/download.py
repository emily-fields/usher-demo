from pathlib import Path

import httpx


def download_file(url: str, dest: Path) -> None:
    print(f"  downloading {url}")
    timeout = httpx.Timeout(60, read=600)
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        with dest.open("wb") as f:
            for chunk in response.iter_bytes(1 << 20):
                f.write(chunk)
