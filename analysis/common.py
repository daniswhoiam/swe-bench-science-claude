"""Shared loaders for the analysis of the Claude Fable 5.2 and Claude Opus 5.5 runs.

Inputs:
- results/per-task.csv (Fable 5.2 xhigh) and results/opus-5.5-max/per-task.csv (Opus 5.5 max):
  one row per task, count-level data only, same columns.
- analysis/data/paper-domains.csv: the 20-domain label per task from Table 5 of the paper
  (arXiv 2608.19799, CC BY 4.0); also copied into per-task.csv.
- The leaderboard's own data (task-matrix.json, benchmark.json, hard70*.json), downloaded
  by analysis/fetch_inputs.py from the site repository at a pinned commit into
  analysis/data/leaderboard/ (not redistributed here; the site has no licence).

Standard library only.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PER_TASK = RESULTS / "per-task.csv"
OPUS_RESULTS = RESULTS / "opus-5.5-max"
OPUS_PER_TASK = OPUS_RESULTS / "per-task.csv"
ANALYSIS = ROOT / "analysis"
OUT = ANALYSIS / "out"
LOCAL_OUT = OUT / "local"  # git-ignored: tables that contain other configurations' per-task results
LB_DIR = ANALYSIS / "data" / "leaderboard"
LB_TASKS = LB_DIR / "task-matrix.json"
LB_CONFIGS = LB_DIR / "benchmark.json"
LB_HARD70 = LB_DIR / "hard70.json"
LB_HARD70_RESULTS = LB_DIR / "hard70-model-results.json"
PAPER_DOMAINS = ANALYSIS / "data" / "paper-domains.csv"

ALL = [f"{i:03d}" for i in range(1, 120)]

# Leaderboard ids of the seven configurations with published per-task results.
LB_NAMES = {
    "gpt-6-astra": "GPT-6 Astra (max), Codex",
    "opus": "Claude-Opus-5 (max), Claude Code",
    "gpt": "GPT-5.6-sol (max), Codex",
    "deepseek-pro": "DeepSeek-V4-Pro (max), Claude Code",
    "kimi": "Kimi-K3 (max), Kimi Code",
    "glm": "GLM-5.2 (max), Codex",
    "qwen-3-8-27b": "Qwen3.8-27B (xhigh), Claude Code",
}
LB_ORDER = list(LB_NAMES)


def _rows(path: Path = PER_TASK) -> list[dict]:
    rows = list(csv.DictReader(path.open()))
    assert [r["task_id"] for r in rows] == ALL, f"{path.relative_to(ROOT)} must list tasks 001-119 in order"
    return rows


def _int(s: str):
    return int(s) if s != "" else None


def _float(s: str):
    return float(s) if s != "" else None


# Anthropic API list prices, USD per million tokens (platform.claude.com/docs/en/about-claude/pricing, read
# 2026-11-24): input, cache write with 5-minute TTL, cache write with 1-hour TTL, cache read, output.
PRICES = {
    "claude-fable-5-2": (8.0, 10.0, 16.0, 0.20, 40.0),
    "claude-opus-5-5": (4.0, 5.0, 8.0, 0.20, 20.0),
}


def list_cost(model: str, usage: dict, share_1h: float) -> float:
    """List-price cost of a session from Claude Code's model_usage totals (inputTokens, cacheCreationInputTokens,
    cacheReadInputTokens, outputTokens), with share_1h of the cache writes at the 1-hour price."""
    p = PRICES[model]
    cw = usage["cacheCreationInputTokens"]
    return (usage["inputTokens"] * p[0] + cw * (1 - share_1h) * p[1] + cw * share_1h * p[2]
            + usage["cacheReadInputTokens"] * p[3] + usage["outputTokens"] * p[4]) / 1e6


HARD70 = {r["task_id"] for r in _rows() if r["hard70"] == "True"}
assert len(HARD70) == 70


def load_opus() -> dict[str, dict]:
    """One flat record per task from results/opus-5.5-max/per-task.csv (same fields as load_fable)."""
    assert {r["task_id"] for r in _rows(OPUS_PER_TASK) if r["hard70"] == "True"} == HARD70
    return load_fable(OPUS_PER_TASK)


def load_fable(path: Path = PER_TASK) -> dict[str, dict]:
    """One flat record per task from results/per-task.csv (or another run's per-task.csv)."""
    out = {}
    for r in _rows(path):
        agent_min = _float(r["agent_min"])
        out[r["task_id"]] = {
            "task": r["task_id"],
            "status": r["status"],
            "pass": r["pass_at_1"] == "1",
            "public_pass": r["public_reproduction_pass"] == "1",
            "has_result": r["private_total"] != "",
            "pub_passed": _int(r["public_passed"]),
            "pub_total": _int(r["public_total"]),
            "priv_passed": _int(r["private_passed"]),
            "priv_total": _int(r["private_total"]),
            "agent_sec": None if agent_min is None else agent_min * 60,
            "timeout": r["status"] == "agent_time_limit",
            "num_turns": _int(r["num_turns"]),
            "n_edits": _int(r["n_edit_tool_calls"]),
            "n_bash_edit_like": _int(r["n_bash_edit_like"]),
            "n_edits_any": (_int(r["n_edit_tool_calls"]) or 0) + (_int(r["n_bash_edit_like"]) or 0),
            "n_tool_calls": _int(r["n_tool_calls"]),
            "n_bash_calls": _int(r["n_bash_calls"]),
            "patch_bytes": _int(r["patch_bytes"]),
            "patch_files": _int(r["patch_files_count"]),
            "input_tokens": _int(r["input_tokens"]),
            "cache_tokens": _int(r["cache_read_tokens"]),
            "output_tokens": _int(r["output_tokens"]),
            "thinking_tokens": _int(r["thinking_tokens"]),
            "peak_context": _int(r["peak_context_tokens"]),
            "cost": _float(r["list_cost_usd"]),
            "subagents": _int(r["subagents_spawned"]),
            "run_pos": int(r["run_order"]) - 1,
            "server": r["server"],
        }
    return out


def load_task_meta() -> dict[str, dict]:
    meta = {r["task_id"]: r for r in _rows()}
    for r in csv.DictReader(PAPER_DOMAINS.open()):
        assert meta[r["task"]]["paper_domain"] == r["paper_domain"], r["task"]
    return meta


def _need(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"{path.relative_to(ROOT)} is missing; run: python -I analysis/fetch_inputs.py")


def load_leaderboard() -> tuple[dict[str, dict[str, dict]], dict]:
    """Per-task results {task: {config: {pub_passed, pub_total, priv_passed, priv_total, pass}}}."""
    _need(LB_TASKS)
    d = json.loads(LB_TASKS.read_text())
    per_task = {}
    for t in d["tasks"]:
        per_task[t["publishedTaskId"]] = {
            m: {
                "pub_passed": r["public"]["passed"], "pub_total": r["public"]["total"],
                "priv_passed": r["private"]["passed"], "priv_total": r["private"]["total"],
                "pass": r["reward"] == 1,
            }
            for m, r in t["results"].items()
        }
    published = {m["id"]: m for m in d["models"]}
    return per_task, published


def load_leaderboard_configs() -> list[dict]:
    _need(LB_CONFIGS)
    return json.loads(LB_CONFIGS.read_text())["models"]


def load_leaderboard_hard70() -> tuple[set[str], dict[str, list[str]]]:
    _need(LB_HARD70)
    ids = set(json.loads(LB_HARD70.read_text())["taskIds"])
    assert ids == HARD70, "per-task.csv hard70 column differs from the leaderboard list"
    passes = json.loads(LB_HARD70_RESULTS.read_text())["modelPasses"]
    return ids, passes


# ---------- small statistics helpers (pure Python) ----------

def binom_two_sided(b: int, c: int) -> float:
    """Exact McNemar: two-sided binomial test of b successes in b+c trials at p=0.5."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (centre - half, centre + half)


def median(xs: list[float]) -> float:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return float("nan")
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def mean(xs: list[float]) -> float:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def pct(k: float, n: float) -> str:
    return f"{100 * k / n:.1f}%" if n else "n/a"
