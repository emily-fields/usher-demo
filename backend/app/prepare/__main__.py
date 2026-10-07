import argparse
import logging
import sys
import time

from app.config import load_settings
from app.prepare.build import prepare_tree
from app.trees import TREE_SPECS, spec_by_key


def _size_mb(path) -> float:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) / 1e6


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download, prune and store the demo trees.")
    parser.add_argument("keys", nargs="*", help=f"tree keys (default: all of {[s.key for s in TREE_SPECS]})")
    parser.add_argument("--size", type=int, default=10_000, help="leaves to keep per tree")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)

    settings = load_settings()
    for key in args.keys or [s.key for s in TREE_SPECS]:
        spec = spec_by_key(key)
        print(f"{key}: preparing {spec.organism}")
        started = time.monotonic()
        directory = prepare_tree(spec, settings, args.size)
        print(f"{key}: done in {time.monotonic() - started:.0f}s, {_size_mb(directory):.1f} MB at {directory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
