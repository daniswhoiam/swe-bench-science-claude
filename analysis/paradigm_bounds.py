"""Bounds on Fable's per-paradigm Pass@1 (Issue / Expert / Engineering).

The benchmark does not publish which task belongs to which paradigm. It does publish
(a) the paradigm sizes (52 Issue-driven, 49 Expert-exploratory, 18 Engineering-integration;
paper Sec. 3), (b) per-paradigm Pass@1 for every leaderboard configuration, and (c) per-task
pass/fail for seven of them. Any true assignment must reproduce (b) from (c). This script
finds, by integer programming, the smallest and largest number of Fable passes in each
paradigm over all assignments that satisfy those constraints. If the interval is wide, the
paradigm split of Fable's result is not identifiable from public data.

Needs numpy and scipy >= 1.9 (the published output was made with scipy 1.18.1):
    <python-with-scipy> -I analysis/paradigm_bounds.py   (after analysis/fetch_inputs.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ALL, HARD70, LB_ORDER, load_fable, load_leaderboard  # noqa: E402

PARADIGMS = ["issue", "expert", "engineering"]
SIZES = {"issue": 52, "expert": 49, "engineering": 18}


def main() -> None:
    fab = load_fable()
    lb, pub = load_leaderboard()
    T, P = len(ALL), len(PARADIGMS)
    idx = lambda t, p: t * P + p  # noqa: E731
    nvar = T * P
    rows, lo, hi = [], [], []

    def eq(coefs: dict[int, float], value: float) -> None:
        row = np.zeros(nvar)
        for k, v in coefs.items():
            row[k] = v
        rows.append(row)
        lo.append(value)
        hi.append(value)

    for ti in range(T):
        eq({idx(ti, p): 1 for p in range(P)}, 1)
    for pi, p in enumerate(PARADIGMS):
        eq({idx(ti, pi): 1 for ti in range(T)}, SIZES[p])
    targets = {}
    for m in LB_ORDER:
        for pi, p in enumerate(PARADIGMS):
            k = pub[m]["scores"][p] / 100 * SIZES[p]
            assert abs(k - round(k)) < 0.02, (m, p, k)
            targets[(m, p)] = round(k)
            eq({idx(ti, pi): 1 for ti, t in enumerate(ALL) if lb[t][m]["pass"]}, round(k))
        assert sum(targets[(m, p)] for p in PARADIGMS) == sum(lb[t][m]["pass"] for t in ALL), m
    A = np.array(rows)
    cons = LinearConstraint(A, lo, hi)
    integrality = np.ones(nvar)
    bounds = Bounds(0, 1)
    print("Published per-paradigm pass counts used as constraints (Issue/Expert/Engineering):")
    for m in LB_ORDER:
        print(f"  {m}: " + "/".join(str(targets[(m, p)]) for p in PARADIGMS))

    fpass = np.array([1.0 if fab[t]["pass"] else 0.0 for t in ALL])
    print("\nFable passes per paradigm over all assignments consistent with the published numbers:")
    results = {}
    for pi, p in enumerate(PARADIGMS):
        c = np.zeros(nvar)
        for ti in range(T):
            c[idx(ti, pi)] = fpass[ti]
        out = []
        for sign in (1, -1):
            r = milp(sign * c, constraints=[cons], integrality=integrality, bounds=bounds)
            assert r.success, r.message
            out.append(int(round(sign * r.fun)))
        results[p] = out
        n = SIZES[p]
        print(f"  {p:12s} min {out[0]:2d}/{n} ({100 * out[0] / n:.1f}%)  max {out[1]:2d}/{n} ({100 * out[1] / n:.1f}%)")

    # Which tasks are forced into a paradigm by the constraints?
    forced = {}
    for ti, t in enumerate(ALL):
        feas = []
        for pi in range(P):
            c = np.zeros(nvar)
            c[idx(ti, pi)] = -1
            r = milp(c, constraints=[cons], integrality=integrality, bounds=bounds)
            feas.append(r.success and round(-r.fun) == 1)
        if sum(feas) == 1:
            forced[t] = PARADIGMS[feas.index(True)]
    print(f"\nTasks whose paradigm is forced by the constraints: {len(forced)} {forced}")
    # Hard70 composition range per paradigm (context)
    h = np.array([1.0 if t in HARD70 else 0.0 for t in ALL])
    for pi, p in enumerate(PARADIGMS):
        c = np.zeros(nvar)
        for ti in range(T):
            c[idx(ti, pi)] = h[ti]
        mn = milp(c, constraints=[cons], integrality=integrality, bounds=bounds)
        mx = milp(-c, constraints=[cons], integrality=integrality, bounds=bounds)
        print(f"  Hard70 tasks in {p}: {round(mn.fun)}-{round(-mx.fun)} of {SIZES[p]}")


if __name__ == "__main__":
    main()
