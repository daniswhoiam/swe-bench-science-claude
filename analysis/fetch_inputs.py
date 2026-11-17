"""Download the leaderboard data the analysis compares against, pinned and hash-checked.

The leaderboard site (github.com/swescience/swescience.github.io) has no licence file, so
its data is not redistributed here. This script downloads four files from the site
repository at a fixed commit and checks them before anything uses them:

- the SHA-256 of the downloaded bytes (pinned to the commit), and
- for task-matrix.json and benchmark.json, the SHA-256 of a canonical JSON form against the
  snapshot the analysis was first run on (saved 2026-11-17 from the live site; its byte
  formatting differs from the repository file, its content does not).

Files land in analysis/data/leaderboard/ (git-ignored). Standard library only.

    python -I analysis/fetch_inputs.py              # download and check
    python -I analysis/fetch_inputs.py --check-only # check files already in place
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "analysis" / "data" / "leaderboard"
SITE_REPO = "swescience/swescience.github.io"
COMMIT = "f16153e5c47c46b2f6f2ebf0aaefae34bdf8c8bd"  # 2026-10-09, leaderboard "updated 2026-10-09"
URL = "https://raw.githubusercontent.com/{repo}/{commit}/data/{name}"

# name -> (sha256 of the raw bytes at COMMIT, sha256 of the canonical JSON of our snapshot or None)
FILES = {
    "task-matrix.json": ("0e339f1aa47ab84e584e9b99047e11ea5e7dac26001bfab1490dd3bc55008cfd",
                         "e11db716fbee846efc8d0cf8269103da8cc8e50bc0d147315fefb9ff764281ef"),
    "benchmark.json": ("d37fa52c31219e104949f140ceb884f7a8c6e98f79cef97c4fc16b7ecc2fc411",
                       "81e129ae0369fff186e6e570da80bf683b572d23fe09f9d7e46c19b26924fe08"),
    "hard70.json": ("32138bf77efd110f8c08b3ee4dcf29dddc63919da23f9026c2b10cec1c81fcef", None),
    "hard70-model-results.json": ("818339ff18728865c44e9da7e3d9d4fdb89581eef39414102fdef9969160be50", None),
}


def _normalise(o):
    """Integral floats become ints, so 25.0 and 25 hash alike."""
    if isinstance(o, float) and o.is_integer():
        return int(o)
    if isinstance(o, list):
        return [_normalise(x) for x in o]
    if isinstance(o, dict):
        return {k: _normalise(v) for k, v in o.items()}
    return o


def canonical_sha256(obj) -> str:
    text = json.dumps(_normalise(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check(name: str, data: bytes) -> list[str]:
    raw_want, canon_want = FILES[name]
    problems = []
    raw = hashlib.sha256(data).hexdigest()
    if raw != raw_want:
        problems.append(f"{name}: raw sha256 {raw} != pinned {raw_want}")
    if canon_want:
        canon = canonical_sha256(json.loads(data))
        if canon != canon_want:
            problems.append(f"{name}: canonical sha256 {canon} != snapshot {canon_want}")
    return problems


def download(url: str, attempts: int = 3) -> bytes:
    """GET with a few retries for dropped connections; the hashes decide whether the bytes are right."""
    for i in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return resp.read()
        except (http.client.IncompleteRead, urllib.error.URLError, TimeoutError) as e:
            if i == attempts - 1:
                raise
            print(f"retrying {url.rsplit('/', 1)[-1]} after {type(e).__name__}", file=sys.stderr)
            time.sleep(2 * (i + 1))
    raise AssertionError("unreachable")


def check_hard70_column() -> list[str]:
    """results/per-task.csv's hard70 column must equal the leaderboard's list."""
    ours = {r["task_id"] for r in csv.DictReader((ROOT / "results" / "per-task.csv").open()) if r["hard70"] == "True"}
    theirs = set(json.loads((DEST / "hard70.json").read_text())["taskIds"])
    return [] if ours == theirs else [f"hard70 column differs from hard70.json: {sorted(ours ^ theirs)}"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check-only", action="store_true", help="do not download; check files in place")
    args = ap.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    problems = []
    for name in FILES:
        path = DEST / name
        if args.check_only:
            data = path.read_bytes()
        else:
            url = URL.format(repo=SITE_REPO, commit=COMMIT, name=name)
            data = download(url)
        p = check(name, data)
        problems += p
        if not p and not args.check_only:
            path.write_bytes(data)
        print(f"{'FAIL' if p else 'ok  '} {name} ({len(data)} bytes)")
    if not problems:
        problems += check_hard70_column()
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"all files match {SITE_REPO}@{COMMIT[:7]} and the analysis snapshot; written to {DEST.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
