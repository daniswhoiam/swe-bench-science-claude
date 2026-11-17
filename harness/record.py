"""Per-run record, built from a finished Pier trial directory.

One record per (task, arm, seed). This is the record builder used for the run, trimmed of
fields that belonged to other experiments (hook and check logs) and of the fields that need
unpatched-base verifier counts.

Only `verifier/reward.json` is read from the verifier directory. The other verifier files
quote hidden test code and must stay unread.

The published results/runs.jsonl is a field subset of these records; see results/README.md.

Rebuild records for existing jobs with:
    python -m harness.record <jobs-dir> --tasks-dir <bench>/tasks-selected-all --out runs.jsonl [--csv runs-summary.csv]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
STAGES = ("environment_setup", "agent_setup", "agent_execution", "verifier")
# The OAuth token prefix, written in two parts so that this repository contains no literal token prefix.
TOKEN_PREFIX = b"sk-" + b"ant-oat"
BASH_EDIT_RE = re.compile(r"\bsed\s+(-\w+\s+)*-\w*i|\bperl\s+-\w*i|\bgit\s+apply\b|\bpatch\s+-p|\btee\s|<<\s*['\"]?\w+|\.write(_text)?\(")
JOB_NAME_RE = re.compile(r"^(?P<arm>[A-Za-z-]+?)-(?P<task>\d{3})-s(?P<seed>\d+)$")


def job_name(arm: str, task: str, seed: int) -> str:
    return f"{arm}-{task}-s{seed}"


def _load(path: Path):
    return json.loads(path.read_text()) if path.is_file() else None


def _seconds(span: dict | None) -> float | None:
    if not span or not span.get("started_at") or not span.get("finished_at"):
        return None
    start = datetime.fromisoformat(span["started_at"])
    end = datetime.fromisoformat(span["finished_at"])
    return round((end - start).total_seconds(), 1)


def _stream_events(path: Path) -> list[dict]:
    events = []
    if path.is_file():
        for line in path.read_text(errors="replace").splitlines():
            if line.startswith("{"):
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def _stream_summary(trial: Path) -> dict:
    events = _stream_events(trial / "agent" / "claude-code.txt")
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    summary = {
        "model": init.get("model"),
        "claude_code_version": init.get("claude_code_version"),
        "has_result_event": result is not None,
    }
    if result:
        usage = result.get("usage") or {}
        summary.update(
            {
                "subtype": result.get("subtype"),
                "is_error": result.get("is_error"),
                "terminal_reason": result.get("terminal_reason"),
                "num_turns": result.get("num_turns"),
                "duration_ms": result.get("duration_ms"),
                "duration_api_ms": result.get("duration_api_ms"),
                # List price as estimated by Claude Code, not what was paid.
                "total_cost_usd": result.get("total_cost_usd"),
                "input_tokens": usage.get("input_tokens"),
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
                "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
                "model_usage": result.get("modelUsage"),
                "subagents_spawned": (result.get("subagent_stats") or {}).get("spawned"),
            }
        )
    return summary


def _edit_summary(trial: Path) -> dict:
    """Edit-tool calls from the trajectory. Edits made through Bash are only estimated."""
    trajectory = _load(trial / "agent" / "trajectory.json") or {}
    by_tool = {tool: 0 for tool in EDIT_TOOLS}
    files: set[str] = set()
    n_tool_calls = n_bash_calls = n_bash_edit_like = 0
    for step in trajectory.get("steps", []):
        for call in step.get("tool_calls") or []:
            n_tool_calls += 1
            name = call.get("function_name")
            if name == "Bash":
                n_bash_calls += 1
                if BASH_EDIT_RE.search((call.get("arguments") or {}).get("command") or ""):
                    n_bash_edit_like += 1
            if name in by_tool:
                by_tool[name] += 1
                args = call.get("arguments") or {}
                path = args.get("file_path") or args.get("notebook_path")
                if path:
                    files.add(path)
    return {
        "n_edits": sum(by_tool.values()),
        "by_tool": by_tool,
        "n_files_edited": len(files),
        "n_tool_calls": n_tool_calls,
        "n_bash_calls": n_bash_calls,
        # Heuristic: Bash commands that look like in-place file edits.
        "n_bash_edit_like": n_bash_edit_like,
    }


def _patch_summary(trial: Path) -> dict:
    patch = trial / "artifacts" / "model.patch"
    if not patch.is_file():
        return {"present": False, "bytes": 0, "sha256": None, "files": []}
    data = patch.read_bytes()
    files = re.findall(rb"^diff --git a/(\S+) b/", data, flags=re.M)
    return {
        "present": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        # Not published (it points to where the fix is); results/ keeps only the count.
        "files": [f.decode(errors="replace") for f in files],
    }


def _network_summary(trial: Path) -> dict:
    agent = verifier = None
    for path in trial.glob("network-policy-*.json"):
        mode = (_load(path) or {}).get("network_mode")
        if path.stem.endswith("__verifier__trial"):
            verifier = mode
        else:
            agent = mode
    return {
        "agent": agent,
        "verifier": verifier,
        "ok": agent == "isolated-allowlist" and verifier == "none",
    }


def count_token_hits(directory: Path) -> int:
    """Number of files under `directory` that contain the OAuth token prefix."""
    hits = 0
    for path in directory.rglob("*"):
        if path.is_file() and not path.is_symlink():
            try:
                if TOKEN_PREFIX in path.read_bytes():
                    hits += 1
            except OSError:
                pass
    return hits


def find_trial(job_dir: Path) -> Path | None:
    trials = sorted(p for p in job_dir.glob("task_*__*") if p.is_dir())
    return trials[0] if trials else None


def build_record(job_dir: Path, *, arm: str, task: str, seed: int, tasks_dir: Path) -> dict:
    """tasks_dir: the materialised task folder the run used (e.g. tasks-selected-all).
    The original builder read task.toml from a fixed tasks-selected folder; it is a
    parameter here."""
    record: dict = {
        "run_id": job_dir.name,
        "task": task,
        "arm": arm,
        "seed": seed,
        "job_dir": str(job_dir),
    }
    trial = find_trial(job_dir)
    if trial is None:
        record["status"] = "no-trial"
        return record

    result = _load(trial / "result.json") or {}
    agent_config = (result.get("config") or {}).get("agent") or {}
    kwargs = agent_config.get("kwargs") or {}
    agent_result = result.get("agent_result") or {}
    exception = result.get("exception_info")
    stream = _stream_summary(trial)
    reward = _load(trial / "verifier" / "reward.json")
    task_toml = (tasks_dir / f"task_{task}" / "task.toml").read_text()
    timeout = re.search(r"\[agent\][^\[]*?timeout_sec\s*=\s*([\d.]+)", task_toml, flags=re.S)

    public = (reward or {}).get("public")
    private = (reward or {}).get("private")
    record.update(
        {
            "status": "error" if exception else ("ok" if reward else "no-reward"),
            "exception_type": (exception or {}).get("exception_type"),
            "trial_name": trial.name,
            "agent_name": agent_config.get("name") or agent_config.get("import_path"),
            "model_id": {
                "requested": agent_config.get("model_name"),
                "reported": stream["model"],
            },
            "effort": kwargs.get("reasoning_effort"),
            "claude_code_version": {
                "requested": kwargs.get("version"),
                "reported": stream["claude_code_version"] or (result.get("agent_info") or {}).get("version"),
            },
            "agent_timeout_sec": float(timeout.group(1)) if timeout else None,
            "started_at": result.get("started_at"),
            "finished_at": result.get("finished_at"),
            "wall_sec": {
                "total": _seconds(result),
                **{stage: _seconds(result.get(stage)) for stage in STAGES},
            },
            "usage": {
                "pier": {
                    key: agent_result.get(key)
                    for key in (
                        "n_input_tokens",
                        "n_cache_tokens",
                        "n_output_tokens",
                        "cost_usd",
                        "peak_context_tokens",
                        "summarization_count",
                        "n_agent_steps",
                    )
                },
                "claude_code": {k: v for k, v in stream.items() if k not in ("model", "claude_code_version")},
            },
            "edits": _edit_summary(trial),
            "patch": _patch_summary(trial),
            "verifier": {
                "reward": (reward or {}).get("reward"),
                "public": public,
                "private": private,
                # The paper's Pass@1: every private test passes. The grader's reward also
                # requires the public script to pass.
                "hidden_pass": bool(private and private.get("collected") and private.get("passed") == private.get("collected")),
                "public_pass": bool(public and public.get("return_code") == 0),
            },
            "network": _network_summary(trial),
            "token_prefix_hits": count_token_hits(job_dir),
        }
    )
    return record


CSV_FIELDS = (
    "run_id", "task", "arm", "seed", "status", "reward", "hidden_pass", "public_pass",
    "private_passed", "private_collected", "wall_total_sec", "agent_sec", "verifier_sec", "num_turns",
    "n_edits", "n_bash_edit_like", "patch_bytes", "input_tokens", "cache_tokens", "output_tokens",
    "list_cost_usd", "network_ok", "token_prefix_hits",
)


def csv_row(record: dict) -> dict:
    verifier = record.get("verifier") or {}
    private = verifier.get("private") or {}
    wall = record.get("wall_sec") or {}
    usage = record.get("usage") or {}
    pier = usage.get("pier") or {}
    return {
        "run_id": record["run_id"],
        "task": record["task"],
        "arm": record["arm"],
        "seed": record["seed"],
        "status": record.get("status"),
        "reward": verifier.get("reward"),
        "hidden_pass": verifier.get("hidden_pass"),
        "public_pass": verifier.get("public_pass"),
        "private_passed": private.get("passed"),
        "private_collected": private.get("collected"),
        "wall_total_sec": wall.get("total"),
        "agent_sec": wall.get("agent_execution"),
        "verifier_sec": wall.get("verifier"),
        "num_turns": (usage.get("claude_code") or {}).get("num_turns"),
        "n_edits": (record.get("edits") or {}).get("n_edits"),
        "n_bash_edit_like": (record.get("edits") or {}).get("n_bash_edit_like"),
        "patch_bytes": (record.get("patch") or {}).get("bytes"),
        "input_tokens": pier.get("n_input_tokens"),
        "cache_tokens": pier.get("n_cache_tokens"),
        "output_tokens": pier.get("n_output_tokens"),
        "list_cost_usd": pier.get("cost_usd"),
        "network_ok": (record.get("network") or {}).get("ok"),
        "token_prefix_hits": record.get("token_prefix_hits"),
    }


def write_outputs(records: list[dict], out: Path, csv_path: Path | None) -> None:
    out.write_text("".join(json.dumps(r) + "\n" for r in records))
    if csv_path:
        with csv_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(csv_row(r) for r in records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("jobs_dir", type=Path)
    parser.add_argument("--tasks-dir", type=Path, required=True, help="materialised tasks, e.g. swe-bench-science/tasks-selected-all")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    records = []
    for job_dir in sorted(p for p in args.jobs_dir.resolve().iterdir() if p.is_dir()):
        match = JOB_NAME_RE.match(job_dir.name)
        if not match:
            continue
        records.append(
            build_record(job_dir, arm=match["arm"], task=match["task"], seed=int(match["seed"]),
                         tasks_dir=args.tasks_dir.resolve())
        )
    write_outputs(records, args.out, args.csv)
    for record in records:
        print(json.dumps(csv_row(record)))


if __name__ == "__main__":
    main()
