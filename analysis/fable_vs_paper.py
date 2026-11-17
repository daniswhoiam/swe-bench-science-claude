"""Claude Fable 5.2 (xhigh) on SWE-bench Science compared with the paper and the leaderboard.

Run from the repository root, after `python -I analysis/fetch_inputs.py`:
    python -I analysis/fable_vs_paper.py [section ...]
Sections: metrics, pertask, slices, failures, cost, extras, chart (default: all).

Count-level data only: results/per-task.csv and the leaderboard's published per-task
results. Writes analysis/out/chart-leaderboard.csv (published aggregates plus this run) and,
into the git-ignored analysis/out/local/, tables that contain other configurations'
per-task results.
"""
from __future__ import annotations

import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ALL, HARD70, LB_NAMES, LB_ORDER, LOCAL_OUT, OUT, binom_two_sided, load_fable, load_leaderboard,
    load_leaderboard_configs, load_leaderboard_hard70, load_task_meta, mean, median, pct, wilson,
)

FAB = load_fable()
META = load_task_meta()
LB, LB_PUB = load_leaderboard()


def fable_as_lb(task: str) -> dict:
    """Fable in the leaderboard's per-task shape. Task 002 (verifier timeout, nothing
    collected) is scored 0 of the leaderboard's totals, which is how the leaderboard
    records runs whose evaluation produced nothing (e.g. Kimi-K3 on 061: 0/1)."""
    f = FAB[task]
    ref = next(iter(LB[task].values()))
    if not f["has_result"]:
        return {"pub_passed": 0, "pub_total": ref["pub_total"], "priv_passed": 0,
                "priv_total": ref["priv_total"], "pass": False}
    return {"pub_passed": f["pub_passed"], "pub_total": f["pub_total"], "priv_passed": f["priv_passed"],
            "priv_total": f["priv_total"], "pass": f["pass"]}


def per_config() -> dict[str, dict[str, dict]]:
    res = {m: {t: LB[t][m] for t in ALL} for m in LB_ORDER}
    res["fable"] = {t: fable_as_lb(t) for t in ALL}
    return res


CFG = per_config()
NAMES = {**LB_NAMES, "fable": "Claude Fable 5.2 (xhigh), Claude Code 2.1.293"}
ORDER = ["fable"] + LB_ORDER


def spearman(xs: list[float], ys: list[float]) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den


# ------------------------------------------------------------------ section: metrics

def section_metrics() -> None:
    print("\n## 1. Leaderboard metrics\n")
    print("Check: do macro means (task-level means) of the published per-task counts reproduce the"
          " published aggregates?\n")
    print("| config | Public (pub / ours) | Private macro (pub / ours) | Private micro | Overall (pub / ours) |")
    print("|---|---|---|---|---|")
    for m in LB_ORDER:
        s = LB_PUB[m]["scores"]
        rows = CFG[m].values()
        pub = 100 * mean([r["pub_passed"] / r["pub_total"] for r in rows])
        priv = 100 * mean([r["priv_passed"] / r["priv_total"] for r in rows])
        micro = 100 * sum(r["priv_passed"] for r in rows) / sum(r["priv_total"] for r in rows)
        ov = 100 * sum(r["pass"] for r in rows) / 119
        print(f"| {m} | {s['public']:.2f} / {pub:.2f} | {s['private']:.2f} / {priv:.2f} | {micro:.2f} |"
              f" {s['overall']:.2f} / {ov:.2f} |")

    print("\nFable, same definitions (002 scored 0 of the leaderboard's totals; variant without 002):\n")
    rows = list(CFG["fable"].values())
    rows_ex = [CFG["fable"][t] for t in ALL if t != "002"]
    for label, rr in (("all 119", rows), ("118 without 002", rows_ex)):
        pub = 100 * mean([r["pub_passed"] / r["pub_total"] for r in rr])
        priv = 100 * mean([r["priv_passed"] / r["priv_total"] for r in rr])
        ov = sum(r["pass"] for r in rr)
        lo, hi = wilson(ov, len(rr))
        print(f"- {label}: Public {pub:.2f}%, Private {priv:.2f}%, Overall {ov}/{len(rr)} = "
              f"{100 * ov / len(rr):.2f}% (Wilson 95% {100 * lo:.1f}-{100 * hi:.1f}%)")
    pub_full = sum(1 for r in rows if r["pub_passed"] == r["pub_total"])
    print(f"- Tasks with every public check passing: {pub_full}/119; public reproduction passes "
          f"(return code 0): {sum(FAB[t]['public_pass'] for t in ALL)}/119")
    print(f"- Pass@1 = verifier reward on all 119: "
          f"{all(FAB[t]['pass'] == (FAB[t]['has_result'] and FAB[t]['priv_passed'] == FAB[t]['priv_total']) for t in ALL)}")

    diffs = [(t, CFG["fable"][t]["priv_total"], LB[t]["opus"]["priv_total"]) for t in ALL
             if FAB[t]["has_result"] and FAB[t]["priv_total"] != LB[t]["opus"]["priv_total"]]
    print(f"- Private-test denominators that differ from the leaderboard's (task, ours, theirs): {diffs}")


# ------------------------------------------------------------------ section: pertask

def section_pertask() -> None:
    print("\n## 2. Per-task comparison with the seven published configurations\n")
    f = {t: CFG["fable"][t]["pass"] for t in ALL}
    print("| config | overall | both | Fable only | config only | neither | exact McNemar p (two-sided) |")
    print("|---|---|---|---|---|---|---|")
    for m in LB_ORDER:
        c = {t: CFG[m][t]["pass"] for t in ALL}
        both = sum(f[t] and c[t] for t in ALL)
        fo = sum(f[t] and not c[t] for t in ALL)
        co = sum(c[t] and not f[t] for t in ALL)
        nei = sum(not f[t] and not c[t] for t in ALL)
        p = binom_two_sided(fo, co)
        print(f"| {m} | {sum(c.values())}/119 | {both} | {fo} | {co} | {nei} | {p:.2g} |")

    rng = random.Random(20261117)
    for m in ("gpt-6-astra", "opus"):
        d = [int(f[t]) - int(CFG[m][t]["pass"]) for t in ALL]
        boots = sorted(sum(rng.choice(d) for _ in d) / 119 for _ in range(20000))
        print(f"- Fable minus {m}: {100 * sum(d) / 119:+.1f} points, paired bootstrap 95% CI "
              f"{100 * boots[500]:+.1f} to {100 * boots[19499]:+.1f}")

    npass = {t: sum(CFG[m][t]["pass"] for m in LB_ORDER) for t in ALL}
    none_solve = [t for t in ALL if npass[t] == 0]
    only_f = sorted(t for t in none_solve if f[t])
    fail_common = sorted(t for t in ALL if not f[t] and npass[t] >= 5)
    print(f"\n- Tasks no published configuration solves: {len(none_solve)}; Fable solves "
          f"{len(only_f)} of them: {only_f}")
    common_fails = [(t, npass[t], "{}/{}".format(FAB[t]["priv_passed"], FAB[t]["priv_total"])) for t in fail_common]
    print(f"- Tasks solved by >=5 of 7 configurations that Fable fails (task, configs, Fable's private checks): "
          f"{common_fails}")
    print(f"- Union of the seven configurations (any passes): {sum(1 for t in ALL if npass[t] > 0)}/119; union incl."
          f" Fable: {sum(1 for t in ALL if npass[t] > 0 or f[t])}/119")
    print(f"- Fable fails although some configuration passes: {sum(1 for t in ALL if not f[t] and npass[t] > 0)}")

    astra = CFG["gpt-6-astra"]
    fo_astra = [t for t in ALL if f[t] and not astra[t]["pass"]]
    missed = Counter(astra[t]["priv_total"] - astra[t]["priv_passed"] for t in fo_astra)
    print(f"- On the {len(fo_astra)} tasks only Fable solves (vs Astra), Astra's missed private checks: "
          f"{dict(sorted(missed.items()))}")

    print("\nFable by number of the seven configurations that pass the task:\n")
    print("| configs passing | tasks | Fable passes | Opus 5 | GPT-6 Astra |")
    print("|---|---|---|---|---|")
    for k in range(8):
        ts = [t for t in ALL if npass[t] == k]
        if ts:
            print(f"| {k} | {len(ts)} | {sum(f[t] for t in ts)} | {sum(CFG['opus'][t]['pass'] for t in ts)} |"
                  f" {sum(CFG['gpt-6-astra'][t]['pass'] for t in ts)} |")

    LOCAL_OUT.mkdir(parents=True, exist_ok=True)
    with (LOCAL_OUT / "per-task-matrix.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["task", "hard70", "fable", *LB_ORDER, "n_configs_pass"])
        for t in ALL:
            w.writerow([t, t in HARD70, int(f[t]), *[int(CFG[m][t]["pass"]) for m in LB_ORDER], npass[t]])


# ------------------------------------------------------------------ section: slices

def slice_table(title: str, groups: dict[str, list[str]], configs=("fable", "gpt-6-astra", "opus")) -> None:
    print(f"\n{title}\n")
    print("| slice | tasks | " + " | ".join(configs) + " |")
    print("|---|---|" + "---|" * len(configs))
    for g, ts in groups.items():
        cells = []
        for m in configs:
            k = sum(CFG[m][t]["pass"] for t in ts)
            cells.append(f"{k} ({pct(k, len(ts))})")
        print(f"| {g} | {len(ts)} | " + " | ".join(cells) + " |")


def section_slices() -> None:
    print("\n## 3. Where the lead comes from\n")
    cfgs = ("fable", "gpt-6-astra", "opus", "gpt", "deepseek-pro")
    slice_table("Hard70 (leaderboard definition):", {
        "Hard70": [t for t in ALL if t in HARD70],
        "other 49": [t for t in ALL if t not in HARD70]}, cfgs)

    doms = defaultdict(list)
    for t in ALL:
        doms[META[t]["paper_domain"]].append(t)
    big = {d: ts for d, ts in sorted(doms.items(), key=lambda x: -len(x[1])) if len(ts) >= 5}
    small = [t for d, ts in doms.items() if len(ts) < 5 for t in ts]
    n_small = sum(1 for ts in doms.values() if len(ts) < 5)
    slice_table("Paper domain (domains with >=5 tasks; the rest pooled):",
                {**big, f"{n_small} smaller domains": small}, cfgs)
    for m in ("opus", "gpt-6-astra"):
        cmp = Counter()
        for ts in doms.values():
            a, b = sum(CFG["fable"][t]["pass"] for t in ts), sum(CFG[m][t]["pass"] for t in ts)
            cmp["above" if a > b else "equal" if a == b else "below"] += 1
        print(f"- Fable vs {m} across the {len(doms)} paper domains: {dict(cmp)}")

    lang = defaultdict(list)
    for t in ALL:
        lang["python" if META[t]["language"] == "python" else "non-pure-python"].append(t)
    slice_table("Language (tasks.csv):", dict(lang), cfgs)

    slice_table("Supplied third-party materials (material_license recorded in tasks.csv):", {
        "materials": [t for t in ALL if META[t]["has_materials"] == "True"],
        "no materials": [t for t in ALL if META[t]["has_materials"] != "True"]}, cfgs)
    slice_table("science_knowledge_ablation flag (91-task ablation subset):", {
        "ablation subset (91)": [t for t in ALL if META[t]["science_knowledge_ablation"] == "True"],
        "not in subset (28)": [t for t in ALL if META[t]["science_knowledge_ablation"] != "True"]}, cfgs)
    slice_table("Licence selection:", {
        "default 96": [t for t in ALL if META[t]["in_default_96"] == "True"],
        "restricted 23": [t for t in ALL if META[t]["restricted_license"] == "True"]}, cfgs)

    def bucket(n):
        return "1-5" if n <= 5 else "6-10" if n <= 10 else "11-20" if n <= 20 else ">20"
    nb = defaultdict(list)
    for t in ALL:
        nb[bucket(LB[t]["opus"]["priv_total"])].append(t)
    slice_table("Number of private checks (leaderboard totals):",
                {k: nb[k] for k in ("1-5", "6-10", "11-20", ">20")}, cfgs)

    first = [t for t in ALL if FAB[t]["server"] == "A"]
    second = [t for t in ALL if FAB[t]["server"] == "B"]
    print(f"\nFable by server: A (i9-13900) {sum(FAB[t]['pass'] for t in first)}/{len(first)}, "
          f"B (i5-12500) {sum(FAB[t]['pass'] for t in second)}/{len(second)}; Hard70 share of server B's tasks "
          f"{sum(t in HARD70 for t in second)}/{len(second)}; server A ran run-order positions "
          f"{sorted(FAB[t]['run_pos'] + 1 for t in first) == list(range(1, 92)) + [93] and '1-91 and 93'}")
    LOCAL_OUT.mkdir(parents=True, exist_ok=True)
    with (LOCAL_OUT / "slices-domain.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["paper_domain", "tasks", *ORDER])
        for d, ts in sorted(doms.items(), key=lambda x: -len(x[1])):
            w.writerow([d, len(ts), *[sum(CFG[m][t]["pass"] for t in ts) for m in ORDER]])


# ------------------------------------------------------------------ section: failures

def failure_profile(m: str) -> dict:
    fails = [t for t in ALL if not CFG[m][t]["pass"]]
    shares, missed = [], []
    for t in fails:
        r = CFG[m][t]
        shares.append(r["priv_passed"] / r["priv_total"])
        missed.append(r["priv_total"] - r["priv_passed"])
    return {"n": len(fails), "mean_share": mean(shares), "median_share": median(shares),
            "miss1": sum(1 for x in missed if x == 1), "miss2": sum(1 for x in missed if x == 2),
            "miss5plus": sum(1 for x in missed if x >= 5), "zero": sum(1 for s in shares if s == 0),
            "ge80": sum(1 for s in shares if s >= 0.8), "fails": fails, "missed": missed}


def section_failures() -> None:
    print("\n## 4. Failure profile\n")
    print("| config | failures | mean share of private checks passed (failures) | median | missed exactly 1 | missed 2 |"
          " missed >=5 | share >=0.8 | 0 passed |")
    print("|---|---|---|---|---|---|---|---|---|")
    for m in ORDER:
        p = failure_profile(m)
        print(f"| {m} | {p['n']} | {p['mean_share']:.3f} | {p['median_share']:.3f} | {p['miss1']} | {p['miss2']} |"
              f" {p['miss5plus']} | {p['ge80']} | {p['zero']} |")
    all_share = {m: mean([CFG[m][t]["priv_passed"] / CFG[m][t]["priv_total"] for t in ALL]) for m in ORDER}
    print("\nMean share of private checks over all 119 tasks: " +
          ", ".join(f"{m} {100 * v:.1f}%" for m, v in all_share.items()))

    f = failure_profile("fable")
    print(f"\nFable failures: {f['n']}; missed-check histogram: {sorted(Counter(f['missed']).items())}")
    tos = [t for t in ALL if FAB[t]["timeout"]]
    print(f"- 90-minute limit: {tos} (passes: {[t for t in tos if FAB[t]['pass']]})")
    print(f"- no verifier result: {[t for t in ALL if not FAB[t]['has_result']]}")
    print(f"- failures whose public reproduction passes: "
          f"{sum(1 for t in f['fails'] if FAB[t]['public_pass'])} of {f['n']}")
    print(f"- failures in Hard70: {sum(1 for t in f['fails'] if t in HARD70)} of {f['n']}")
    npass = {t: sum(CFG[m][t]["pass"] for m in LB_ORDER) for t in ALL}
    print(f"- failures on tasks no published config solves: {sum(1 for t in f['fails'] if npass[t] == 0)}")
    astra_1 = [t for t in ALL if not CFG["gpt-6-astra"][t]["pass"]
               and CFG["gpt-6-astra"][t]["priv_total"] - CFG["gpt-6-astra"][t]["priv_passed"] == 1]
    fable_1 = [t for t, k in zip(f["fails"], f["missed"]) if k == 1]
    print(f"- one-check misses: Fable {len(fable_1)}, Astra {len(astra_1)}; Astra solves "
          f"{sum(CFG['gpt-6-astra'][t]['pass'] for t in fable_1)} of Fable's")
    LOCAL_OUT.mkdir(parents=True, exist_ok=True)
    with (LOCAL_OUT / "fable-failures.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["task", "hard70", "priv_passed", "priv_total", "missed", "agent_min", "n_configs_pass",
                    "opus5_share", "astra_share"])
        for t in f["fails"]:
            r = CFG["fable"][t]
            w.writerow([t, t in HARD70, r["priv_passed"], r["priv_total"], r["priv_total"] - r["priv_passed"],
                        round((FAB[t]["agent_sec"] or 0) / 60, 1), npass[t],
                        round(CFG["opus"][t]["priv_passed"] / CFG["opus"][t]["priv_total"], 3),
                        round(CFG["gpt-6-astra"][t]["priv_passed"] / CFG["gpt-6-astra"][t]["priv_total"], 3)])

    for m, label in (("opus", "Opus 5"), ("gpt-6-astra", "Astra")):
        both = [t for t in ALL if not CFG["fable"][t]["pass"] and not CFG[m][t]["pass"]]
        fs = [CFG["fable"][t]["priv_passed"] / CFG["fable"][t]["priv_total"] for t in both]
        os_ = [CFG[m][t]["priv_passed"] / CFG[m][t]["priv_total"] for t in both]
        print(f"- tasks failed by both Fable and {label}: {len(both)}; mean share Fable {mean(fs):.3f} vs {label}"
              f" {mean(os_):.3f}; Fable higher on {sum(a > b for a, b in zip(fs, os_))}, lower on "
              f"{sum(a < b for a, b in zip(fs, os_))}")


# ------------------------------------------------------------------ section: cost

def describe(label: str, xs: list[float], scale: float = 1.0, unit: str = "") -> str:
    xs = [x for x in xs if x is not None]
    return f"{label}: mean {mean(xs) / scale:.2f}{unit}, median {median(xs) / scale:.2f}{unit} (n={len(xs)})"


def section_cost() -> None:
    print("\n## 5. Behaviour and cost (mechanical metrics)\n")
    fields = [("input_tokens", 1e6, "M"), ("output_tokens", 1e3, "k"), ("cost", 1, " USD"),
              ("agent_sec", 60, " min"), ("num_turns", 1, ""), ("n_edits_any", 1, ""), ("patch_bytes", 1e3, " kB"),
              ("thinking_tokens", 1e3, "k"), ("peak_context", 1e3, "k")]
    fab = list(FAB.values())
    print("Fable, all 119:")
    for k, s, u in fields:
        print("- " + describe(k, [r[k] for r in fab], s, u))
    print(f"- total list cost {sum(r['cost'] or 0 for r in fab):.0f} USD over {sum(1 for r in fab if r['cost'] is not None)}"
          f" runs that report it; tasks with a subagent: {sum(1 for r in fab if (r['subagents'] or 0) > 0)}; "
          f"files in patch median {median([r['patch_files'] for r in fab])}")
    print("\nFable pass vs fail (medians):\n")
    print("| metric | pass (75) | fail (44) | fail, Hard70 only |")
    print("|---|---|---|---|")
    for k, s, u in fields:
        p = median([r[k] for r in fab if r["pass"]])
        f = median([r[k] for r in fab if not r["pass"]])
        fh = median([r[k] for r in fab if not r["pass"] and r["task"] in HARD70])
        print(f"| {k} | {p / s:.2f}{u} | {f / s:.2f}{u} | {fh / s:.2f}{u} |")

    print("\nLeaderboard token means (millions per task, input / output):")
    configs = load_leaderboard_configs()
    for c in configs:
        print(f"- {c['family']} ({c.get('reasoningDepth')}, {c['harness']}): {c['tokens']['input']:.3f} / "
              f"{c['tokens']['output']:.3f}; overall {c['scores']['overall']}")
    f_in = mean([r["input_tokens"] for r in fab]) / 1e6
    f_out = mean([r["output_tokens"] for r in fab]) / 1e6
    print(f"- Fable 5.2 (xhigh): {f_in:.3f} / {f_out:.3f}; overall {100 * sum(r['pass'] for r in fab) / 119:.2f}")
    ov = [c["scores"]["overall"] for c in configs] + [100 * sum(r["pass"] for r in fab) / 119]
    ins = [c["tokens"]["input"] for c in configs] + [f_in]
    outs = [c["tokens"]["output"] for c in configs] + [f_out]
    print(f"- Spearman rank correlation of Pass@1 over {len(ov)} configurations: with input tokens "
          f"{spearman(ov, ins):.2f}, with output tokens {spearman(ov, outs):.2f}")


# ------------------------------------------------------------------ section: extras

def mcnemar_line(label: str, ts: list[str], a: dict[str, bool], b: dict[str, bool]) -> str:
    ao = sum(a[t] and not b[t] for t in ts)
    bo = sum(b[t] and not a[t] for t in ts)
    return (f"{label}: {sum(a[t] for t in ts)} vs {sum(b[t] for t in ts)} of {len(ts)}; discordant {ao}-{bo}, "
            f"exact McNemar p = {binom_two_sided(ao, bo):.2g}")


def section_extras() -> None:
    print("\n## Extras: sensitivity and subsets\n")
    f = {t: CFG["fable"][t]["pass"] for t in ALL}
    astra = {t: CFG["gpt-6-astra"][t]["pass"] for t in ALL}
    opus5 = {t: CFG["opus"][t]["pass"] for t in ALL}
    h70 = sorted(HARD70)
    rest = [t for t in ALL if t not in HARD70]
    print("- " + mcnemar_line("Hard70, Fable vs Astra", h70, f, astra))
    print("- " + mcnemar_line("Hard70, Fable vs Opus 5", h70, f, opus5))
    print("- " + mcnemar_line("other 49, Fable vs Astra", rest, f, astra))
    print("- " + mcnemar_line("other 49, Fable vs Opus 5", rest, f, opus5))
    f_to = {t: f[t] and not FAB[t]["timeout"] for t in ALL}
    print(f"- Sensitivity, the 3 runs that hit the 90-minute limit counted as failures: {sum(f_to.values())}/119 "
          f"= {100 * sum(f_to.values()) / 119:.1f}%")
    print("  " + mcnemar_line("vs Astra", ALL, f_to, astra))
    print("  " + mcnemar_line("vs Opus 5", ALL, f_to, opus5))
    print(f"- Fable-fails / config-passes tasks: vs Opus 5 {[t for t in ALL if opus5[t] and not f[t]]}; "
          f"vs Astra {[t for t in ALL if astra[t] and not f[t]]}")


# ------------------------------------------------------------------ section: chart

def section_chart() -> None:
    """Aggregate rows for the figure: the 17 published configurations plus this run.
    Hard70 Pass@1 is computed from the leaderboard's own per-task data (task-matrix.json for
    the seven configurations with per-task results, hard70-model-results.json for three
    more); the other seven are below 20% and have no Hard70 value on the leaderboard."""
    hard70_ids, hard70_passes = load_leaderboard_hard70()
    h70 = {m: 100 * sum(LB[t][m]["pass"] for t in hard70_ids) / 70 for m in LB_ORDER}
    h70.update({m: 100 * len(set(ps) & hard70_ids) / 70 for m, ps in hard70_passes.items()})
    src = "swescience.github.io leaderboard, data at site commit f16153e (updated 2026-10-09)"
    fab = list(FAB.values())
    rows = [["Claude Fable 5.2", "Claude Code 2.1.293", "xhigh", f"{100 * sum(r['pass'] for r in fab) / 119:.2f}",
             f"{100 * sum(FAB[t]['pass'] for t in hard70_ids) / 70:.2f}",
             f"{mean([r['input_tokens'] for r in fab]) / 1e6:.3f}",
             f"{mean([r['output_tokens'] for r in fab]) / 1e6:.3f}",
             "this run (results/); one attempt per task; not run by the benchmark authors"]]
    for c in load_leaderboard_configs():
        h = h70.get(c["id"])
        rows.append([c["family"], c["harness"], c.get("reasoningDepth") or "default", f"{c['scores']['overall']:.2f}",
                     f"{h:.2f}" if h is not None else "", f"{c['tokens']['input']:.3f}",
                     f"{c['tokens']['output']:.3f}", src])
    rows.sort(key=lambda r: -float(r[3]))
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "chart-leaderboard.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["configuration", "harness", "effort", "overall_pass_at_1_pct", "hard70_pass_at_1_pct",
                    "input_tokens_per_task_millions", "output_tokens_per_task_millions", "source"])
        w.writerows(rows)
    print(f"\nwrote {path.relative_to(OUT.parents[1])} ({len(rows)} rows); Hard70 Pass@1: "
          + ", ".join(f"{r[0]} ({r[2]}) {r[4]}" for r in rows if r[4]))


SECTIONS = {"metrics": section_metrics, "pertask": section_pertask, "slices": section_slices,
            "failures": section_failures, "cost": section_cost, "extras": section_extras, "chart": section_chart}

if __name__ == "__main__":
    for name in (sys.argv[1:] or list(SECTIONS)):
        SECTIONS[name]()
