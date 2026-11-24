"""Check this run's leaderboard-format files the way the leaderboard site checks its data.

Re-implements the checks that apply to a per-task entry (119 tasks with three-digit IDs,
macro public/private means equal to the stated scores, mean reward equal to the overall
Pass@1, Hard70 pass list consistent with the matrix) and, if the leaderboard data has been
downloaded (analysis/fetch_inputs.py), merges the entry into a copy of the site's
task-matrix.json in memory to show it fits. Nothing is written.

    python -I leaderboard-format/validate_entry.py              # Fable 5.2 (xhigh)
    python -I leaderboard-format/validate_entry.py --run opus   # Opus 5.5 (max), files in opus-5.5-max/

Exit code 0 when every check passes. The site's own validator would still reject the
entry because Fail2Pass, Pass2Pass and the paradigm scores are null: only the maintainers
can compute them (see leaderboard-format/README.md).
"""
from __future__ import annotations

import copy
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MATRIX = HERE / "task-matrix-entry.json"
HARD70 = HERE / "hard70-entry.json"
BENCH = HERE / "benchmark-entry.json"
PER_TASK = ROOT / "results" / "per-task.csv"
LB = ROOT / "analysis" / "data" / "leaderboard" / "task-matrix.json"
NULL_OK = {"fail2Pass", "pass2Pass", "issue", "expert", "engineering"}

problems: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        problems.append(msg)


def main() -> int:
    global MATRIX, HARD70, BENCH, PER_TASK
    if "--run" in sys.argv and sys.argv[sys.argv.index("--run") + 1] == "opus":
        sub = HERE / "opus-5.5-max"
        MATRIX, HARD70, BENCH = sub / "task-matrix-entry.json", sub / "hard70-entry.json", sub / "benchmark-entry.json"
        PER_TASK = ROOT / "results" / "opus-5.5-max" / "per-task.csv"
    print(f"checking {MATRIX.relative_to(ROOT)} against {PER_TASK.relative_to(ROOT)}")
    m = json.loads(MATRIX.read_text())
    h = json.loads(HARD70.read_text())
    b = json.loads(BENCH.read_text())
    model = m["models"][0]
    mid = model["id"]
    tasks = m["tasks"]
    ids = [t["publishedTaskId"] for t in tasks]

    check(len(m["models"]) == 1 and model == b, "benchmark-entry.json equals the model object in task-matrix-entry.json")
    check(ids == [f"{i:03d}" for i in range(1, 120)], "119 tasks, IDs 001-119, three digits, in order")
    rows = [t["results"][mid] for t in tasks]
    shape_ok = all(
        set(r) == {"public", "private", "reward", "transition", "source"}
        and r["reward"] in (0, 1) and r["transition"] is None
        and 0 <= r["public"]["passed"] <= r["public"]["total"] and r["public"]["total"] > 0
        and 0 <= r["private"]["passed"] <= r["private"]["total"] and r["private"]["total"] > 0
        for r in rows)
    check(shape_ok, "every result has public/private passed<=total (total>0), reward 0/1, transition null, source")
    check(all(r["reward"] == int(r["private"]["passed"] == r["private"]["total"]) for r in rows),
          "reward = 1 exactly when every private test passes")
    pub = round(100 * sum(r["public"]["passed"] / r["public"]["total"] for r in rows) / 119, 2)
    priv = round(100 * sum(r["private"]["passed"] / r["private"]["total"] for r in rows) / 119, 2)
    overall = round(100 * sum(r["reward"] for r in rows) / 119, 2)
    s = model["scores"]
    check(pub == s["public"], f"public macro {pub} = stated {s['public']}")
    check(priv == s["private"], f"private macro {priv} = stated {s['private']}")
    check(overall == s["overall"], f"Pass@1 {overall} = stated overall {s['overall']}")
    check(all(s[k] is None for k in NULL_OK) and all(s[k] is not None for k in s if k not in NULL_OK),
          "only Fail2Pass, Pass2Pass and the paradigm scores are null")
    passes = sorted(t["publishedTaskId"] for t in tasks if t["results"][mid]["reward"] == 1)
    check(h["taskCount"] == 119 and sorted(h["modelPasses"][mid]) == passes,
          f"hard70-entry.json lists the {len(passes)} passed tasks")

    per_task = {r["task_id"]: r for r in csv.DictReader(PER_TASK.open())}
    agree = True
    for t, r in zip(ids, rows):
        p = per_task[t]
        if p["private_total"]:
            agree &= (r["public"]["passed"], r["public"]["total"], r["private"]["passed"], r["private"]["total"],
                      r["reward"]) == (int(p["public_passed"]), int(p["public_total"]), int(p["private_passed"]),
                                       int(p["private_total"]), int(p["pass_at_1"]))
        else:
            agree &= r["reward"] == 0 and r["public"]["passed"] == 0 and r["private"]["passed"] == 0
    check(agree, f"entry agrees with {PER_TASK.relative_to(ROOT)} (a run without a verifier result: 0 of the leaderboard's totals)")
    tok_in = round(sum(int(p["input_tokens"]) for p in per_task.values()) / 119 / 1e6, 3)
    tok_out = round(sum(int(p["output_tokens"]) for p in per_task.values()) / 119 / 1e6, 3)
    check(model["tokens"] == {"input": tok_in, "output": tok_out}, f"tokens = per-task means ({tok_in}M / {tok_out}M)")

    if LB.is_file():
        lb = json.loads(LB.read_text())
        merged = copy.deepcopy(lb)
        check(mid not in {x["id"] for x in lb["models"]}, f"model id {mid!r} is new on the leaderboard")
        by_id = {t["publishedTaskId"]: t for t in merged["tasks"]}
        check(set(by_id) == set(ids), "same 119 task IDs as the leaderboard")
        check(all(by_id[t["publishedTaskId"]]["scientificKnowledgeAblation"] == t["scientificKnowledgeAblation"]
                  for t in tasks), "scientificKnowledgeAblation flags match the leaderboard")
        diffs = []
        for t in tasks:
            ref = next(iter(by_id[t["publishedTaskId"]]["results"].values()))
            r = t["results"][mid]
            if (r["public"]["total"], r["private"]["total"]) != (ref["public"]["total"], ref["private"]["total"]):
                diffs.append((t["publishedTaskId"], r["private"]["total"], ref["private"]["total"]))
            by_id[t["publishedTaskId"]]["results"][mid] = r
        merged["models"].append(model)
        check(diffs == [("032", 6, 21)], f"test totals equal the leaderboard's except 032 (ours 6, theirs 21): {diffs}")
        check(all(len(t["results"]) == len(lb["models"]) + 1 for t in merged["tasks"]),
              f"merged matrix has {len(lb['models']) + 1} configurations on every task")
    else:
        print("skip merge test: run analysis/fetch_inputs.py first")

    print("\nall checks passed" if not problems else f"\n{len(problems)} check(s) failed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
