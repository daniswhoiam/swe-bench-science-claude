"""Claude Opus 5.5 at medium, high and max effort: the earlier runs in results/opus-5.5-effort/, against the
Opus 5.5 max pass (results/opus-5.5-max/) and the Fable 5.2 xhigh pass (results/).

    python -I analysis/opus_effort.py           # prints, and writes results/opus-5.5-effort/summary.json
    python -I analysis/opus_effort.py --check   # fails if summary.json differs

The earlier runs have several runs per task at medium (2 to 4 for most tasks, 1 for 18 tasks) and one run at high
and at max on 18 tasks. Run-to-run variation is measured from the tasks with at least two medium runs.
"""
from __future__ import annotations

import csv
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ALL, HARD70, RESULTS, binom_two_sided, load_fable, load_opus, mean, median, wilson  # noqa: E402

EFFORT = RESULTS / "opus-5.5-effort"
SUMMARY = EFFORT / "summary.json"


def r1(x: float) -> float:
    return round(x, 1)


def main() -> int:
    runs = list(csv.DictReader((EFFORT / "per-run.csv").open()))
    fable = {t: r["pass"] for t, r in load_fable().items()}
    omax = {t: r["pass"] for t, r in load_opus().items()}
    by = defaultdict(list)  # (effort, task) -> [(seed, pass)]
    for r in runs:
        by[(r["effort"], r["task_id"])].append((int(r["seed"]), r["pass_at_1"] == "1"))
    out: dict = {"runs": {e: sum(1 for r in runs if r["effort"] == e) for e in ("medium", "high", "max")}}

    # ---------------- medium on all 119 tasks ----------------
    med = {t: sorted(by[("medium", t)]) for t in ALL}
    assert all(med[t] for t in ALL), "medium must cover all 119 tasks"
    n_runs = Counter(len(v) for v in med.values())
    first = {t: med[t][0][1] for t in ALL}  # lowest seed = first run of the task
    k1 = sum(first.values())
    lo, hi = wilson(k1, 119)
    rate = {t: mean([p for _, p in med[t]]) for t in ALL}
    anyp = sum(any(p for _, p in med[t]) for t in ALL)
    multi = [t for t in ALL if len(med[t]) >= 2]
    always = [t for t in multi if all(p for _, p in med[t])]
    never = [t for t in multi if not any(p for _, p in med[t])]
    mixed = [t for t in multi if t not in always and t not in never]
    exp_disc = sum(2 * sum(p for _, p in med[t]) * (len(med[t]) - sum(p for _, p in med[t]))
                   / (len(med[t]) * (len(med[t]) - 1)) for t in multi)
    print(f"Opus 5.5 medium: {out['runs']['medium']} runs on 119 tasks (runs per task: {dict(sorted(n_runs.items()))})")
    print(f"  first run per task: Pass@1 {k1}/119 = {100 * k1 / 119:.1f}% (Wilson 95% {100 * lo:.1f}-{100 * hi:.1f})")
    print(f"  mean over tasks of the per-task pass rate: {100 * mean(list(rate.values())):.1f}%; "
          f"solved by at least one run: {anyp}/119")
    print(f"  {len(multi)} tasks with >= 2 runs: always pass {len(always)}, never {len(never)}, mixed {len(mixed)} {mixed}")
    print(f"  expected number of these tasks on which two runs disagree: {exp_disc:.1f} ({100 * exp_disc / len(multi):.1f}%)")
    pairs = []
    for a, b in itertools.combinations(sorted({s for v in med.values() for s, _ in v}), 2):
        common_t = [t for t in ALL if a in dict(med[t]) and b in dict(med[t])]
        if len(common_t) < 20:
            continue
        x = sum(dict(med[t])[a] and not dict(med[t])[b] for t in common_t)
        y = sum(dict(med[t])[b] and not dict(med[t])[a] for t in common_t)
        pairs.append({"seeds": [a, b], "tasks": len(common_t), "passes": [sum(dict(med[t])[a] for t in common_t),
                      sum(dict(med[t])[b] for t in common_t)], "discordant": [x, y]})
        print(f"  seed {a} vs seed {b}: {len(common_t)} tasks, passes {pairs[-1]['passes']}, discordant {x}+{y}, "
              f"exact McNemar p {binom_two_sided(x, y):.2g}")
    mins = [float(r["agent_min"]) for r in runs if r["effort"] == "medium" and r["agent_min"]]
    costs = [float(r["list_cost_usd"]) for r in runs if r["effort"] == "medium" and r["list_cost_usd"]]
    print(f"  agent minutes median {median(mins):.1f} (Mac, emulated images); list cost median ${median(costs):.2f}, "
          f"mean ${mean(costs):.2f} over {len(costs)} runs")
    out["medium"] = {
        "first_run_pass_at_1": {"passed": k1, "tasks": 119, "pct": r1(100 * k1 / 119), "wilson95": [r1(100 * lo), r1(100 * hi)]},
        "mean_task_pass_rate_pct": r1(100 * mean(list(rate.values()))),
        "solved_by_any_run": anyp,
        "runs_per_task": {str(k): v for k, v in sorted(n_runs.items())},
        "tasks_with_2plus_runs": {"tasks": len(multi), "always": len(always), "never": len(never), "mixed": mixed},
        "expected_disagreement_between_two_runs": round(exp_disc, 1),
        "seed_pairs": pairs,
        "time_limit_runs": sorted(r["run_id"] for r in runs if r["effort"] == "medium" and r["status"] == "agent_time_limit"),
        "list_cost_usd": {"median": round(median(costs), 2), "mean": round(mean(costs), 2), "runs_reporting": len(costs)},
    }

    # ---------------- high and max on the 18 tasks ----------------
    t18 = sorted(t for t in ALL if by[("max", t)])
    assert len(t18) == 18 and all(len(by[("high", t)]) == 1 for t in t18)
    hp = {t: by[("high", t)][0][1] for t in t18}
    xp = {t: by[("max", t)][0][1] for t in t18}
    print(f"\n18 tasks with runs at every effort: medium first run {sum(first[t] for t in t18)}, high {sum(hp.values())}, "
          f"max (earlier run) {sum(xp.values())}, max (full pass) {sum(omax[t] for t in t18)}, "
          f"Fable 5.2 xhigh {sum(fable[t] for t in t18)}")
    same = [t for t in t18 if xp[t] != omax[t]]
    print(f"  Opus 5.5 max twice (earlier run and full pass): tasks with a different outcome {len(same)} {same}")
    out["eighteen_tasks"] = {"tasks": t18, "medium_first_run": sum(first[t] for t in t18), "high": sum(hp.values()),
                             "max_earlier": sum(xp.values()), "max_full_pass": sum(omax[t] for t in t18),
                             "fable_xhigh": sum(fable[t] for t in t18), "max_runs_disagree": same}

    # ---------------- medium against max and Fable 5.2 on all 119 ----------------
    print("\nAll 119 tasks:")
    for name, other in (("Opus 5.5 max (full pass)", omax), ("Fable 5.2 xhigh", fable)):
        a = sum(other[t] and not first[t] for t in ALL)
        b = sum(first[t] and not other[t] for t in ALL)
        nv = [t for t in never if other[t]]
        al = [t for t in always if not other[t]]
        h = sum(other[t] for t in HARD70) - sum(first[t] for t in HARD70)
        print(f"  {name} {sum(other.values())}/119 vs medium first run {k1}/119: only {name.split(' (')[0]} {a}, only medium {b}, "
              f"exact McNemar p {binom_two_sided(a, b):.2g}; Hard70 difference {h:+d}; solves {len(nv)} of the {len(never)} "
              f"tasks medium never solved; fails {len(al)} of the {len(always)} it always solved {al}")
        out[f"vs_{'opus_max' if 'Opus' in name else 'fable_xhigh'}"] = {"only_other": a, "only_medium": b,
                                                                       "solves_medium_never": len(nv), "fails_medium_always": al}
    disagree_fo = sum(fable[t] != omax[t] for t in multi)
    print(f"  Fable 5.2 xhigh and Opus 5.5 max disagree on {disagree_fo} of the {len(multi)} tasks with >= 2 medium runs "
          f"(two medium runs: {exp_disc:.1f} expected)")
    out["fable_vs_opus_max_disagree_on_multi_tasks"] = disagree_fo

    text = json.dumps(out, indent=1) + "\n"
    if "--check" in sys.argv:
        if SUMMARY.read_text() != text:
            print(f"{SUMMARY.relative_to(RESULTS.parent)} differs")
            return 1
        print(f"{SUMMARY.relative_to(RESULTS.parent)} matches")
        return 0
    SUMMARY.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
