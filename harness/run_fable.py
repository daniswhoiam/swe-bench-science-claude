"""Driver for the Claude Fable 5.2 xhigh pass (arm FXH): one Pier job per task.

This is the driver used for the run, trimmed to the one configuration that was scored.
Each task is its own Pier job (`pier run`, the benchmark's built-in `claude-code` agent),
started with a clean environment because Pier falls back to the host's ANTHROPIC_* and
CLAUDE_* variables. Task images are pulled before a task starts and removed after it.

    python -m harness.run_fable --bench swe-bench-science --tasks-dir tasks-selected-all \
        --run-dir runs/fable-xhigh --order provenance/run-order.json --concurrency 7
    python -m harness.run_fable ... --dry-run          # print the Pier command for one task

Outputs under --run-dir: jobs/FXH-<task>-s1/ (Pier job), logs/<job>.log (Pier console
output), runs.jsonl and runs-summary.csv (records, harness/record.py), order.json.
Finished jobs are skipped, so the command can be re-run after an interruption.

Set-aside rule (decided before the run; it reads only the session's own error text, never
the verifier result):
- A session whose final Claude Code result is an error that mentions a usage or rate limit
  is moved to <run-dir>/infra-failures/, the driver waits 30 minutes and reruns the task
  from scratch. This does not use up a retry.
- Any other session error, a session that fails within 90 seconds, or an agent that never
  started is also set aside and rerun from scratch (at most INFRA_RETRIES times), then the
  driver halts. Set-aside sessions are never recorded or scored.
- A file named STOP in --run-dir lets running jobs finish and starts no new one.
Runs that hit the 90-minute agent limit are recorded and scored on their workspace, as
Pier does.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from harness.record import TOKEN_PREFIX, build_record, csv_row, job_name, write_outputs

# ---- the frozen configuration ----
ARM = "FXH"
SEED = 1
MODEL = "anthropic/claude-fable-5-2"
EFFORT = "xhigh"
CLAUDE_CODE_VERSION = "2.1.293"
AGENT_ENV = {"CLAUDE_CODE_MAX_OUTPUT_TOKENS": "128000"}
ENVIRONMENT = "harness.environment:MirroredScienceBenchDocker"
ORDER_SEED = 20261111
PLATFORM = "linux/amd64"

ROOT = Path(__file__).resolve().parent.parent  # repository root (holds harness/)
DEFAULT_ENV_FILE = Path.home() / ".config" / "swe-bench-science" / "claude.env"

INFRA_RETRIES = 2
MIN_FREE_GB = 10
LIMIT_WAIT_SEC = 1800
LIMIT_WAITS_MAX = 60  # 30 hours of waiting per entry before the driver halts
DOCKER_RATE_LIMIT_WAIT_SEC = 600
DOCKER_RATE_LIMIT_RETRIES = 12
# Usage or rate limit in the session's final error text. Until the first limit stop of the
# run, the final "\blimit\b" alternative was missing, so the limit message was not
# recognised: those sessions went down the general set-aside path instead (set aside,
# rerun from scratch, never scored), and the driver halted after two retries. See
# provenance/run-log.md.
LIMIT_WORDS = re.compile(r"usage limit|limit reached|rate.?limit|\b429\b|quota|overloaded|\b529\b|credit balance|hit your limit|limit will reset|reached your [\w .-]{0,40}limit|\blimit\b", re.I)

_lock = threading.Lock()
_pull_lock = threading.Lock()
_active: dict[str, int] = {}
_halt = threading.Event()


class Paths:
    bench: Path
    tasks: Path
    run_dir: Path
    env_file: Path
    pier: Path


P = Paths()


def say(**fields) -> None:
    print(json.dumps({"t": time.strftime("%H:%M:%S"), **fields}), flush=True)


def pier_command(task: str, job: str) -> list[str]:
    return [
        str(P.pier), "run",
        "--path", str(P.tasks / f"task_{task}"),
        "--env", "docker",
        "--environment-import-path", ENVIRONMENT,
        "--environment-kwarg", "inference_urls=[]",
        "--agent", "claude-code",
        "--agent-kwarg", f"version={CLAUDE_CODE_VERSION}",
        "--agent-kwarg", f"reasoning_effort={EFFORT}",
        "--model", MODEL,
        "--env-file", str(P.env_file),
        "--n-concurrent", "1", "--n-attempts", "1", "--max-retries", "0",
        "--no-force-build", "--no-delete", "--yes",
        "--jobs-dir", str(P.run_dir / "jobs"), "--job-name", job,
        *[arg for key, value in AGENT_ENV.items() for arg in ("--agent-env", f"{key}={value}")],
    ]


def run_pier(command: list[str], log_path: Path) -> int:
    """Run Pier with a clean environment; its console output goes to log_path."""
    env = {
        "HOME": os.environ["HOME"],
        "PATH": os.environ["PATH"],
        "DOCKER_DEFAULT_PLATFORM": PLATFORM,
        # the benchmark's scripts.pier_network and this repository's harness package
        "PYTHONPATH": f"{P.bench}{os.pathsep}{ROOT}",
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("wb") as log:
        return subprocess.run(
            command, cwd=P.bench, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT
        ).returncode


# ---- images ----

def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def pull(ref: str) -> dict:
    """Pull one image, waiting out Docker Hub's anonymous rate limit if needed."""
    if _run(["docker", "image", "inspect", ref]).returncode == 0:
        return {"ok": True, "cached": True}
    for _ in range(DOCKER_RATE_LIMIT_RETRIES + 1):
        done = _run(["docker", "pull", "--platform", PLATFORM, ref])
        if done.returncode == 0:
            return {"ok": True, "cached": False}
        if not re.search(r"toomanyrequests|too many requests|rate limit|\b429\b", done.stdout, re.I):
            return {"ok": False, "error": done.stdout[-600:]}
        time.sleep(DOCKER_RATE_LIMIT_WAIT_SEC)
    return {"ok": False, "error": "Docker Hub rate limit did not clear"}


def image_refs(task: str) -> list[str]:
    config = tomllib.loads((P.tasks / f"task_{task}" / "task.toml").read_text())
    return [config["environment"]["docker_image"], config["verifier"]["environment"]["docker_image"]]


def acquire(task: str) -> None:
    while shutil.disk_usage(P.run_dir).free < MIN_FREE_GB * 1e9 and not _halt.is_set():
        say(task=task, waiting=f"under {MIN_FREE_GB} GB free on disk")
        time.sleep(120)
    with _lock:
        _active[task] = _active.get(task, 0) + 1
    with _pull_lock:  # one pull at a time against Docker Hub
        for ref in image_refs(task):
            result = pull(ref)
            if not result["ok"]:
                raise RuntimeError(f"pull failed for task {task}: {result.get('error')}")


def release(task: str) -> None:
    with _lock:
        _active[task] -= 1
        if _active[task]:
            return
        listed = subprocess.run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], capture_output=True, text=True).stdout
        derived = [name for name in listed.split() if name.startswith(f"task_{task}__")]
        for ref in derived + image_refs(task):
            subprocess.run(["docker", "image", "rm", ref], capture_output=True)
        subprocess.run(["docker", "builder", "prune", "-f"], capture_output=True)


# ---- the set-aside rule ----

def agent_started(record: dict) -> bool:
    return (record.get("wall_sec") or {}).get("agent_execution") is not None


def failed_fast(record: dict) -> bool:
    stream = ((record.get("usage") or {}).get("claude_code")) or {}
    seconds = (record.get("wall_sec") or {}).get("agent_execution") or 0
    return seconds < 90 and (stream.get("is_error") or not stream.get("has_result_event"))


def session_error(job: str) -> str | None:
    """Text of the session's final result if it ended in an error (API error, usage limit), else None."""
    text = None
    for path in (P.run_dir / "jobs" / job).glob("task_*/agent/claude-code.txt"):
        for line in path.read_text(errors="replace").splitlines():
            if '"type":"result"' in line.replace(" ", ""):
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                text = str(event.get("result") or "")[:300] if event.get("is_error") else None
    return text


def run_once(task: str) -> dict:
    job = job_name(ARM, task, SEED)
    log_path = P.run_dir / "logs" / f"{job}.log"
    exit_code = run_pier(pier_command(task, job), log_path)
    record = build_record(P.run_dir / "jobs" / job, arm=ARM, task=task, seed=SEED, tasks_dir=P.tasks)
    record["pier_exit_code"] = exit_code
    record["token_prefix_hits"] = record.get("token_prefix_hits", 0) + int(TOKEN_PREFIX in log_path.read_bytes())
    return record


def set_aside(job: str) -> None:
    target = P.run_dir / "infra-failures"
    target.mkdir(exist_ok=True)
    n = 1
    while (target / f"{job}-{n}").exists():
        n += 1
    if (P.run_dir / "jobs" / job).exists():
        shutil.move(P.run_dir / "jobs" / job, target / f"{job}-{n}")
    log = P.run_dir / "logs" / f"{job}.log"
    if log.is_file():
        shutil.move(log, target / f"{job}-{n}.log")


def do_entry(entry: dict) -> None:
    task = entry["task"]
    job = job_name(ARM, task, SEED)
    with _lock:
        _active[task] = _active.get(task, 0)  # keep key present
    try:
        if _halt.is_set() or (P.run_dir / "STOP").exists() or (P.run_dir / "jobs" / job).exists():
            return
        acquire(task)
        try:
            record = None
            attempts = waits = 0
            while attempts <= INFRA_RETRIES and waits <= LIMIT_WAITS_MAX and not _halt.is_set():
                record = run_once(task)
                error = session_error(job) if agent_started(record) else None
                if error is not None and LIMIT_WORDS.search(error):
                    # usage or rate limit: never a result; keep nothing, wait, rerun (does not use up retries)
                    set_aside(job)
                    waits += 1
                    say(job=job, limit_hit=True, wait_sec=LIMIT_WAIT_SEC, waits=waits)
                    record = None
                    time.sleep(LIMIT_WAIT_SEC)
                    continue
                # strict: a session that ends in any API error is never recorded as a result
                if agent_started(record) and not failed_fast(record) and error is None:
                    break
                reason = ("session error" if error is not None and agent_started(record) and not failed_fast(record)
                          else "session failed fast" if agent_started(record) else "agent never started")
                set_aside(job)
                say(job=job, infra_failure=reason)
                record = None
                attempts += 1
                if reason == "session failed fast":
                    time.sleep(600)  # most likely a usage limit; wait before retrying
            if record is None:
                _halt.set()
                say(job=job, HALT="failure persisted; no further work is started")
                return
            with _lock:
                runs_path = P.run_dir / "runs.jsonl"
                records = [json.loads(line) for line in runs_path.read_text().splitlines()] if runs_path.is_file() else []
                records.append(record)
                write_outputs(records, runs_path, P.run_dir / "runs-summary.csv")
            row = csv_row(record)
            say(**{k: row.get(k) for k in ("run_id", "status", "hidden_pass", "public_pass", "private_passed",
                                            "private_collected", "agent_sec", "num_turns", "list_cost_usd")})
        finally:
            release(task)
    except BaseException as error:
        say(job=job, driver_error=repr(error)[:400])


def run_order(tasks: list[str], order_file: Path | None) -> list[dict]:
    """The published order (provenance/run-order.json) is this shuffle of 001..119."""
    if order_file:
        entries = json.loads(order_file.read_text())
        wanted = set(tasks)
        return [e for e in entries if e["task"] in wanted]
    rng = random.Random(ORDER_SEED)
    shuffled = sorted(tasks)
    rng.shuffle(shuffled)
    return [dict(task=t, arm=ARM, seed=SEED) for t in shuffled]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bench", type=Path, default=Path("swe-bench-science"), help="the downloaded dataset repository")
    parser.add_argument("--tasks-dir", default="tasks-selected-all", help="materialised tasks under --bench")
    parser.add_argument("--run-dir", type=Path, required=True, help="output folder (jobs/, logs/, runs.jsonl)")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="credential file, outside the repository")
    parser.add_argument("--pier", type=Path, default=Path(sys.executable).parent / "pier")
    parser.add_argument("--tasks", nargs="+", default=[f"{i:03d}" for i in range(1, 120)])
    parser.add_argument("--order", type=Path, help="order file (default: seeded shuffle, seed 20261111)")
    parser.add_argument("--concurrency", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true", help="print the order and one Pier command, run nothing")
    args = parser.parse_args()

    P.bench = args.bench.resolve()
    P.tasks = P.bench / args.tasks_dir
    P.run_dir = args.run_dir.resolve()
    P.env_file = args.env_file.expanduser().resolve()
    P.pier = args.pier.resolve() if args.pier.exists() else args.pier
    entries = run_order(args.tasks, args.order)
    if args.dry_run:
        print(json.dumps([e["task"] for e in entries]))
        first = entries[0]["task"]
        print(" ".join(pier_command(first, job_name(ARM, first, SEED))))
        return
    for sub in ("jobs", "logs"):
        (P.run_dir / sub).mkdir(parents=True, exist_ok=True)
    (P.run_dir / "order.json").write_text(json.dumps(entries, indent=1))
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for future in [pool.submit(do_entry, entry) for entry in entries]:
            future.result()
    say(done=True, halted=_halt.is_set())
    raise SystemExit(1 if _halt.is_set() else 0)


if __name__ == "__main__":
    main()
