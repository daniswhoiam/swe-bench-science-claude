"""Claude Opus 5.5 (max) against the leaderboard and against the Fable 5.2 run, task by task.

Reproduces every Opus 5.5 number in the README from results/opus-5.5-max/, results/ (Fable 5.2)
and the leaderboard's own data (run analysis/fetch_inputs.py first). Prints only; writes nothing.

    python -I analysis/opus_vs_paper.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (ALL, HARD70, LB_NAMES, LB_ORDER, binom_two_sided, load_fable,  # noqa: E402
                    load_leaderboard, load_leaderboard_configs, load_leaderboard_hard70, load_opus, wilson)


def pct(k: int, n: int) -> str:
    return f"{100 * k / n:.2f}%"


def main() -> None:
    opus, fable = load_opus(), load_fable()
    lb, _ = load_leaderboard()
    load_leaderboard_hard70()  # checks that the Hard70 list matches per-task.csv
    o = {t: opus[t]["pass"] for t in ALL}
    k = sum(o.values())
    lo, hi = wilson(k, 119)
    kh = sum(o[t] for t in HARD70)
    print(f"Opus 5.5 max: Pass@1 {k}/119 = {pct(k, 119)} (Wilson 95% {100 * lo:.1f}-{100 * hi:.1f}); "
          f"Hard70 {kh}/70 = {pct(kh, 70)}; other 49 {k - kh}/49 = {pct(k - kh, 49)}")

    timeouts = [t for t in ALL if opus[t]["timeout"]]
    o_strict = {t: o[t] and not opus[t]["timeout"] for t in ALL}
    print(f"time-limit runs {timeouts}, passing {[t for t in timeouts if o[t]]}; "
          f"scored as failures: {sum(o_strict.values())}/119 = {pct(sum(o_strict.values()), 119)}")

    configs = {m["id"]: m for m in load_leaderboard_configs()}
    rank = sorted([m["scores"]["overall"] for m in configs.values()] + [100 * k / 119], reverse=True)
    print(f"rank among the 17 leaderboard configurations plus this run: {rank.index(100 * k / 119) + 1} of {len(rank)}")

    def compare(name: str, other: dict[str, bool], mine: dict[str, bool] = o) -> None:
        a = sum(mine[t] and not other[t] for t in ALL)
        b = sum(other[t] and not mine[t] for t in ALL)
        both = sum(mine[t] and other[t] for t in ALL)
        ko = sum(other.values())
        print(f"  vs {name:38s} {ko:3d}/119  both {both:3d}  only Opus 5.5 {a:2d}  only other {b:2d}  "
              f"exact McNemar p = {binom_two_sided(a, b):.4g}")

    print("\nTask-by-task (all 119 tasks):")
    compare("Claude Fable 5.2, xhigh (this repository)", {t: fable[t]["pass"] for t in ALL})
    for m in LB_ORDER:
        compare(LB_NAMES[m], {t: lb[t][m]["pass"] for t in ALL})
    print("\nSame, with Opus 5.5's time-limit runs scored as failures:")
    for m in ("gpt-6-astra", "opus"):
        compare(LB_NAMES[m], {t: lb[t][m]["pass"] for t in ALL}, o_strict)

    print("\nHard70 only:")
    for name, other in [("Claude Fable 5.2, xhigh", {t: fable[t]["pass"] for t in ALL}),
                        (LB_NAMES["gpt-6-astra"], {t: lb[t]["gpt-6-astra"]["pass"] for t in ALL}),
                        (LB_NAMES["opus"], {t: lb[t]["opus"]["pass"] for t in ALL})]:
        a = sum(o[t] and not other[t] for t in HARD70)
        b = sum(other[t] and not o[t] for t in HARD70)
        print(f"  vs {name:38s} {sum(other[t] for t in HARD70):2d}/70  only Opus 5.5 {a:2d}  only other {b:2d}  "
              f"p = {binom_two_sided(a, b):.4g}")

    unsolved = [t for t in ALL if not any(lb[t][m]["pass"] for m in LB_ORDER)]
    print(f"\n{len(unsolved)} tasks unsolved by all seven configurations with per-task results; "
          f"Opus 5.5 solves {[t for t in unsolved if o[t]]}; Fable 5.2 solves {[t for t in unsolved if fable[t]['pass']]}")
    either = sum(o[t] or fable[t]["pass"] for t in ALL)
    print(f"solved by Opus 5.5 or Fable 5.2: {either}/119; by both: {sum(o[t] and fable[t]['pass'] for t in ALL)}")


if __name__ == "__main__":
    main()
