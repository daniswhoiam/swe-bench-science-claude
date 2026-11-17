"""Mechanical behaviour metrics from agent trajectories (counts only, no content is printed).

NOT RUNNABLE FROM THIS REPOSITORY ALONE. It reads each run's agent/trajectory.json, and the
trajectories are not published (see README, "Not included"). The code is here so that the
committed counts in analysis/out/tool-mix.csv can be checked by anyone who has the job
folders, such as the benchmark maintainers.

For every run it counts tool calls by name, Bash commands that execute Python or pytest,
Bash commands that mention the public reproduction script, Write calls outside the source
tree (scratch files), source edits, and the time of the first source edit relative to the
session. Command strings are matched by regular expressions inside this script and never
printed.

    python -I analysis/tool_mix.py --jobs-dir <run-dir>/jobs [--out analysis/out/tool-mix.csv]
    python -I analysis/tool_mix.py --summary     # medians from the committed CSV (no trajectories needed)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HARD70, OUT, load_fable, median  # noqa: E402

RUN_PY = re.compile(r"\b(python3?|pytest)\b")
REPRO = re.compile(r"reproduc")
SED_SOURCE = re.compile(r"(\bsed\s+(-\w+\s+)*-\w*i|\bperl\s+-\w*i|\bgit\s+apply\b|\bpatch\s+-p)[^\n]*source/")
HEREDOC_SOURCE = re.compile(r"(>|tee\s+)\s*\S*source/\S+")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def summarise(traj_path: Path) -> dict | None:
    if not traj_path.is_file():
        return None
    steps = json.loads(traj_path.read_text()).get("steps", [])
    stamps = [ts(s["timestamp"]) for s in steps if s.get("timestamp")]
    if len(stamps) < 2:
        return None
    t0, t1 = stamps[0], stamps[-1]
    tools = Counter()
    run_py = repro = scratch_writes = source_edits = 0
    first_edit = None
    for s in steps:
        for c in s.get("tool_calls") or []:
            name = c.get("function_name") or "?"
            tools[name] += 1
            args = c.get("arguments") or {}
            is_source_edit = False
            if name == "Bash":
                cmd = args.get("command") or ""
                if RUN_PY.search(cmd):
                    run_py += 1
                if REPRO.search(cmd):
                    repro += 1
                if SED_SOURCE.search(cmd) or HEREDOC_SOURCE.search(cmd):
                    is_source_edit = True
            elif name in EDIT_TOOLS:
                path = args.get("file_path") or args.get("notebook_path") or ""
                if "/source/" in path:
                    is_source_edit = True
                elif name == "Write":
                    scratch_writes += 1
            if is_source_edit:
                source_edits += 1
                if first_edit is None and s.get("timestamp"):
                    first_edit = ts(s["timestamp"])
    span = (t1 - t0).total_seconds()
    return {
        "tool_calls": sum(tools.values()),
        "bash": tools["Bash"], "read": tools["Read"], "grep_glob": tools["Grep"] + tools["Glob"],
        "edit_tools": sum(tools[k] for k in EDIT_TOOLS), "subagent": tools["Task"] + tools["Agent"],
        "todo": tools["TodoWrite"], "run_python": run_py, "reproduce_mentions": repro,
        "scratch_writes": scratch_writes, "source_edits": source_edits,
        "first_source_edit_min": (first_edit - t0).total_seconds() / 60 if first_edit else None,
        "first_source_edit_frac": (first_edit - t0).total_seconds() / span if first_edit and span > 0 else None,
        "session_min": span / 60,
    }


def fmt(v):
    if v is None:
        return ""
    return f"{v:.4f}" if isinstance(v, float) else v


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs-dir", type=Path, required=True, help="folder with the FXH-<task>-s1 job folders")
    ap.add_argument("--out", type=Path, default=OUT / "tool-mix.csv")
    args = ap.parse_args()
    fab = load_fable()
    rows = []
    for t, f in sorted(fab.items()):
        job = args.jobs_dir / f"FXH-{t}-s1"
        trial = next(iter(sorted(job.glob("task_*__*"))), None)
        s = summarise(trial / "agent" / "trajectory.json") if trial else None
        if s:
            rows.append({"task": t, "pass": f["pass"], **{k: fmt(v) for k, v in s.items()}})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print_summary(args.out)


def print_summary(path: Path) -> None:
    """Medians from a tool-mix CSV (works on the committed file without trajectories)."""
    rows = list(csv.DictReader(path.open()))
    num = lambda r, k: float(r[k]) if r[k] != "" else None  # noqa: E731
    keys = ["tool_calls", "bash", "read", "grep_glob", "edit_tools", "run_python", "reproduce_mentions",
            "scratch_writes", "source_edits", "first_source_edit_min", "first_source_edit_frac", "session_min",
            "subagent", "todo"]
    print(f"trajectories: {len(rows)}\n")
    print("| metric (median) | all | pass | fail |")
    print("|---|---|---|---|")
    for k in keys:
        a = [num(r, k) for r in rows]
        p = [num(r, k) for r in rows if r["pass"] == "True"]
        f = [num(r, k) for r in rows if r["pass"] != "True"]
        print(f"| {k} | {median(a):.2f} | {median(p):.2f} | {median(f):.2f} |")
    print(f"\nruns without a detected source edit: {sum(1 for r in rows if r['first_source_edit_min'] == '')}; "
          f"with a subagent call: {sum(1 for r in rows if num(r, 'subagent'))}; "
          f"with TodoWrite: {sum(1 for r in rows if num(r, 'todo'))}")
    h = [r for r in rows if r["task"] in HARD70]
    print("Hard70 medians pass/fail: " + ", ".join(
        f"{k} {median([num(r, k) for r in h if r['pass'] == 'True']):.1f}/"
        f"{median([num(r, k) for r in h if r['pass'] != 'True']):.1f}"
        for k in ("run_python", "scratch_writes", "first_source_edit_min", "session_min")))


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--summary":
        print_summary(OUT / "tool-mix.csv")
    else:
        main()
