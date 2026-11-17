"""Headline aggregates of the run, from results/ alone (no leaderboard data needed).

    python -I analysis/summarise.py            # writes results/summary.json and prints it
    python -I analysis/summarise.py --check    # fails if results/summary.json differs

Conventions:
- Pass@1 per task = the verifier's reward (every private test passes, and the public
  reproduction passes); they coincide on all 119 tasks.
- Public/private macro = mean over the 119 tasks of the share of tests passed. Task 002
  (verifier timeout, no result) counts as 0, the leaderboard's convention for an
  evaluation that produced nothing.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ALL, HARD70, RESULTS, load_fable, load_task_meta, mean, median, wilson  # noqa: E402


def r2(x: float) -> float:
    return round(x, 2)


def build() -> dict:
    fab = load_fable()
    meta = load_task_meta()
    runs = [json.loads(line) for line in (RESULTS / "runs.jsonl").read_text().splitlines()]
    assert len(runs) == 119
    passed = [t for t in ALL if fab[t]["pass"]]
    k = len(passed)
    lo, hi = wilson(k, 119)

    def subset(ts):
        ts = list(ts)
        n = sum(fab[t]["pass"] for t in ts)
        return {"passed": n, "tasks": len(ts), "percent": r2(100 * n / len(ts))}

    pub_share = [(f["pub_passed"] / f["pub_total"]) if f["has_result"] else 0.0 for f in fab.values()]
    priv_share = [(f["priv_passed"] / f["priv_total"]) if f["has_result"] else 0.0 for f in fab.values()]
    fails = [t for t in ALL if not fab[t]["pass"]]
    timeouts = [t for t in ALL if fab[t]["timeout"]]
    no_timeout_pass = sum(1 for t in passed if not fab[t]["timeout"])
    costs = [f["cost"] for f in fab.values() if f["cost"] is not None]
    web = [mu.get("webSearchRequests") for r in runs
           for mu in ((r["usage"]["claude_code"] or {}).get("model_usage") or {}).values()]
    models_used = sorted({m for r in runs for m in ((r["usage"]["claude_code"] or {}).get("model_usage") or {})})
    inp = [f["input_tokens"] for f in fab.values()]
    cache = [f["cache_tokens"] for f in fab.values()]

    return {
        "configuration": {
            "model": "anthropic/claude-fable-5-2", "effort": "xhigh", "claude_code": "2.1.293",
            "runner": "datacurve-pier 0.3.0, built-in claude-code agent", "tasks": 119, "attempts_per_task": 1,
        },
        "pass_at_1": {"passed": k, "tasks": 119, "percent": r2(100 * k / 119),
                      "wilson95_percent": [round(100 * lo, 1), round(100 * hi, 1)]},
        "hard70": subset(t for t in ALL if t in HARD70),
        "other49": subset(t for t in ALL if t not in HARD70),
        "default96": subset(t for t in ALL if meta[t]["in_default_96"] == "True"),
        "restricted23": subset(t for t in ALL if meta[t]["restricted_license"] == "True"),
        "public_macro_percent": r2(100 * mean(pub_share)),
        "private_macro_percent": r2(100 * mean(priv_share)),
        "public_reproduction_passed": sum(f["public_pass"] for f in fab.values()),
        "status": dict(sorted(Counter(f["status"] for f in fab.values()).items())),
        "agent_time_limit_runs": {"tasks": timeouts, "passed": sum(fab[t]["pass"] for t in timeouts)},
        "sensitivity_time_limit_runs_as_failures": {"passed": no_timeout_pass,
                                                    "percent": round(100 * no_timeout_pass / 119, 1)},
        "verifier_timeout_runs": [t for t in ALL if fab[t]["status"] == "verifier_timeout"],
        "failures": {
            "count": len(fails),
            "public_reproduction_passes": sum(fab[t]["public_pass"] for t in fails),
            "in_hard70": sum(t in HARD70 for t in fails),
            "mean_share_private_passed": round(mean([priv_share[ALL.index(t)] for t in fails]), 3),
        },
        "by_server": {s: subset(t for t in ALL if fab[t]["server"] == s) for s in ("A", "B")},
        "agent_minutes": {"mean": round(mean([f["agent_sec"] / 60 for f in fab.values()]), 1),
                          "median": round(median([f["agent_sec"] / 60 for f in fab.values()]), 1)},
        "tokens_per_task": {
            "input_incl_cache_reads_mean_millions": round(mean(inp) / 1e6, 3),
            "cache_read_share_of_all_input": round(sum(cache) / sum(inp), 3),
            "cache_read_share_mean_per_task": round(mean([b / a for a, b in zip(inp, cache)]), 3),
            "uncached_input_mean_millions": round(mean([a - b for a, b in zip(inp, cache)]) / 1e6, 3),
            "output_mean_millions": round(mean([f["output_tokens"] for f in fab.values()]) / 1e6, 3),
            "thinking_mean_thousands": round(mean([f["thinking_tokens"] for f in fab.values()]) / 1e3),
        },
        "list_cost_usd": {"runs_reporting": len(costs), "total": round(sum(costs)),
                          "mean_per_run": r2(mean(costs))},
        "integrity": {
            "agent_network_isolated_allowlist": sum(r["network"]["agent"] == "isolated-allowlist" for r in runs),
            "verifier_network_none": sum(r["network"]["verifier"] == "none" for r in runs),
            "runs_reporting_web_search_requests": len(web),
            "web_search_requests_total": sum(web),
            "models_in_usage_reports": models_used,
            "token_prefix_hits": sum(r["token_prefix_hits"] for r in runs),
        },
    }


def main() -> int:
    summary = build()
    text = json.dumps(summary, indent=1) + "\n"
    path = RESULTS / "summary.json"
    if "--check" in sys.argv:
        if path.read_text() != text:
            print("results/summary.json differs from a fresh computation", file=sys.stderr)
            return 1
        print("results/summary.json matches")
        return 0
    path.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
