"""Build the two figures with matplotlib (PNG at 2x).

fig1-leaderboard: Pass@1 of all 17 leaderboard configurations plus the two runs in this repository (ranked bars,
                  Fable 5.2 and Opus 5.5 highlighted).
fig2-subsets:     Fable 5.2, Opus 5.5, GPT-6 Astra and Claude Opus 5 on all 119 tasks, Hard70 and the other 49.

Data: results/per-task.csv (Fable 5.2), results/opus-5.5-max/per-task.csv (Opus 5.5) and the leaderboard's own data, downloaded by analysis/fetch_inputs.py into
analysis/data/leaderboard/ (benchmark.json: the 17 configurations; task-matrix.json: per-task results;
hard70.json: the Hard70 list).
Palette and mark specs follow the dataviz reference instance (light mode; slots 1-3 validated: all checks pass,
aqua below 3:1 on the surface -> every bar in fig2 carries a visible value label).

Layout is written in CSS pixels on a 728 px wide canvas (y grows downwards) and saved at 2x (1456 px wide).
Usage, from the repository root (requires matplotlib; the published PNGs were made with matplotlib 3.11.2):
    python -I analysis/fetch_inputs.py
    python -I figures/make_figures.py
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path as MPath

ROOT = Path(__file__).resolve().parents[1]
LB = ROOT / "analysis" / "data" / "leaderboard"
OUT = Path(__file__).resolve().parent

SURFACE = "#ffffff"  # Substack's page is white
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
NEUTRAL_BAR = "#c9c7bf"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
VIOLET = "#7b4fd0"  # fig2 only: Opus 5.5 (contrast 5.6:1 on white; every bar is labelled)
FONTS = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]
W = 728            # canvas width in CSS px
PX_PER_IN = 100    # 1 CSS px = 0.01 in
SCALE = 2          # saved at 2x -> 1456 px wide
PT = 72 / PX_PER_IN  # points per CSS px

for _name in ("benchmark.json", "task-matrix.json", "hard70.json"):
    if not (LB / _name).is_file():
        raise SystemExit(f"{(LB / _name).relative_to(ROOT)} is missing; run: python -I analysis/fetch_inputs.py")
PER_TASK = list(csv.DictReader(open(ROOT / "results" / "per-task.csv")))
OPUS_TASK = list(csv.DictReader(open(ROOT / "results" / "opus-5.5-max" / "per-task.csv")))
HARD70 = set(json.load(open(LB / "hard70.json"))["taskIds"])
assert len(HARD70) == 70 and HARD70 == {r["task_id"] for r in PER_TASK if r["hard70"] == "True"}

plt.rcParams.update({"font.family": FONTS, "svg.fonttype": "none"})


class Canvas:
    """A figure addressed in CSS pixels, origin top-left."""

    def __init__(self, height):
        self.h = height
        self.fig = plt.figure(figsize=(W / PX_PER_IN, height / PX_PER_IN), dpi=PX_PER_IN * SCALE, facecolor=SURFACE)
        self.ax = self.fig.add_axes((0, 0, 1, 1))
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(height, 0)
        self.ax.axis("off")

    def text(self, x, y, s, size=13, color=INK, anchor="left", weight="normal"):
        self.ax.text(x, y, s, fontsize=size * PT, color=color, ha=anchor, va="baseline", fontweight=weight)

    def vline(self, x, y0, y1, color):
        self.ax.plot([x, x], [y0, y1], color=color, linewidth=1 * PT, solid_capstyle="butt", zorder=0.5)

    def bar(self, x0, y, length, h, color, r=4):
        """Horizontal bar anchored at x0, rounded only at the data end."""
        if length <= 0:
            return
        r = min(r, length, h / 2)
        x1 = x0 + length
        verts = [(x0, y), (x1 - r, y), (x1, y), (x1, y + r), (x1, y + h - r), (x1, y + h), (x1 - r, y + h),
                 (x0, y + h), (x0, y)]
        codes = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CURVE3, MPath.CURVE3,
                 MPath.LINETO, MPath.CLOSEPOLY]
        self.ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none"))

    def swatch(self, x, y, size, color):
        self.ax.add_patch(Rectangle((x, y), size, size, facecolor=color, edgecolor="none"))

    def save(self, name):
        for ext in ("png",):
            self.fig.savefig(OUT / f"{name}.{ext}", dpi=PX_PER_IN * SCALE, facecolor=SURFACE,
                             metadata={"Software": None} if ext == "png" else {"Date": None, "Creator": None})
        plt.close(self.fig)


def fig1():
    n_pass = sum(r["pass_at_1"] == "1" for r in PER_TASK)
    n_opus = sum(r["pass_at_1"] == "1" for r in OPUS_TASK)
    rows = [{"configuration": "Claude Fable 5.2", "harness": "Claude Code", "effort": "xhigh",
             "overall_pass_at_1_pct": f"{100 * n_pass / 119:.2f}"},
            {"configuration": "Claude Opus 5.5", "harness": "Claude Code", "effort": "max",
             "overall_pass_at_1_pct": f"{100 * n_opus / 119:.2f}"}]
    for m in json.load(open(LB / "benchmark.json"))["models"]:
        rows.append({"configuration": m["family"], "harness": m["harness"], "effort": m.get("reasoningDepth") or "default",
                     "overall_pass_at_1_pct": f"{m['scores']['overall']:.2f}"})
    assert len(rows) == 19
    rows.sort(key=lambda r: -float(r["overall_pass_at_1_pct"]))
    pad, label_w, plot_r = 24, 268, W - 70
    top, row_h, bar_h = 92, 26, 16
    x0 = pad + label_w + 12
    vmax = 70.0
    sx = lambda v: x0 + (plot_r - x0) * v / vmax
    plot_bottom = top + row_h * len(rows)
    height = plot_bottom + 30 + 46
    c = Canvas(height)
    c.text(pad, 34, "SWE-bench Science: share of the 119 tasks fully solved (Pass@1)", 19, INK, weight="bold")
    c.text(pad, 56, "Fable 5.2 and Opus 5.5: independent runs in this repository (Claude Code, one attempt per task).", 13, INK2)
    c.text(pad, 74, "All other rows: official leaderboard, run by the benchmark authors (updated 9 Oct 2026).", 13, INK2)
    for v in range(0, 71, 10):
        c.vline(sx(v), top - 6, plot_bottom, AXIS if v == 0 else GRID)
        c.text(sx(v), plot_bottom + 18, f"{v}%", 12, MUTED, "center")
    labelled = {"Claude Fable 5.2", "Claude Opus 5.5", "GPT-6 Astra", "Claude-Opus-5"}
    for i, r in enumerate(rows):
        name = r["configuration"].replace("Claude-Opus-5", "Claude Opus 5")
        harness = r["harness"].replace(" 2.1.293", "")
        effort = r["effort"] if r["effort"] not in ("", "default") else ""
        is_ours = r["configuration"] in ("Claude Fable 5.2", "Claude Opus 5.5")  # runs in this repository
        label = f"{name} · {harness}" + (f" · {effort}" if effort else "")
        cy = top + i * row_h + row_h / 2
        c.text(pad + label_w, cy + 4.5, label, 12.5, INK if is_ours else INK2, "right", "bold" if is_ours else "normal")
        v = float(r["overall_pass_at_1_pct"])
        c.bar(x0, cy - bar_h / 2, sx(v) - x0, bar_h, BLUE if is_ours else NEUTRAL_BAR)
        if r["configuration"] in labelled:
            c.text(sx(v) + 6, cy + 4.5, f"{v:.1f}%", 12.5, INK if is_ours else INK2, "left",
                   "bold" if is_ours else "normal")
    c.text(pad, height - 26, "Sources: swescience.github.io leaderboard (17 configurations); Fable 5.2 and Opus 5.5 rows: this repository,", 11, MUTED)
    c.text(pad, height - 11, "not official leaderboard entries. Settings differ (effort, harness version, hardware); see the README.", 11, MUTED)
    c.save("fig1-leaderboard")
    return height


def fig2():
    fable = {r["task_id"]: r["pass_at_1"] == "1" for r in PER_TASK}
    opus = {r["task_id"]: r["pass_at_1"] == "1" for r in OPUS_TASK}
    matrix = json.load(open(LB / "task-matrix.json"))
    lb = {t["publishedTaskId"]: t["results"] for t in matrix["tasks"]}
    solved = {
        "Claude Fable 5.2": lambda t: fable[t],
        "Claude Opus 5.5": lambda t: opus[t],
        "GPT-6 Astra": lambda t: lb[t]["gpt-6-astra"]["reward"] == 1,
        "Claude Opus 5": lambda t: lb[t]["opus"]["reward"] == 1,
    }
    ours = {"Claude Fable 5.2", "Claude Opus 5.5"}  # the runs in this repository
    colors = {"Claude Fable 5.2": BLUE, "Claude Opus 5.5": VIOLET, "GPT-6 Astra": ORANGE, "Claude Opus 5": AQUA}
    legend = {"Claude Fable 5.2": "Claude Fable 5.2 \u00b7 xhigh (this repository)",
              "Claude Opus 5.5": "Claude Opus 5.5 \u00b7 max (this repository)",
              "GPT-6 Astra": "GPT-6 Astra \u00b7 max (leaderboard)", "Claude Opus 5": "Claude Opus 5 \u00b7 max (leaderboard)"}
    groups = [("All 119 tasks", sorted(fable)), ("Hard70 (the 70 hardest)", sorted(HARD70)),
              ("Other 49 tasks", sorted(set(fable) - HARD70))]
    data = {g: {m: (sum(f(t) for t in ts), len(ts)) for m, f in solved.items()} for g, ts in groups}
    assert data["All 119 tasks"]["Claude Fable 5.2"] == (75, 119) and data["All 119 tasks"]["Claude Opus 5.5"] == (71, 119)
    assert data["All 119 tasks"]["GPT-6 Astra"][0] == 60 and data["All 119 tasks"]["Claude Opus 5"][0] == 57
    for g, _ in groups:  # the title's claim: both runs above both leaderboard configurations on every subset
        assert min(data[g][m][0] for m in ours) > max(data[g][m][0] for m in solved if m not in ours), g

    pad, label_w, plot_r = 24, 168, W - 112
    top, bar_h, gap, group_gap = 138, 16, 2, 22
    x0 = pad + label_w + 12
    sx = lambda v: x0 + (plot_r - x0) * v / 100.0
    group_h = 4 * bar_h + 3 * gap
    plot_bottom = top + len(groups) * group_h + (len(groups) - 1) * group_gap + 6
    height = plot_bottom + 30 + 46
    c = Canvas(height)
    c.text(pad, 34, "Both runs lead the leaderboard on every subset", 19, INK, weight="bold")
    c.text(pad, 56, "Pass@1 (share of tasks fully solved); tasks solved in brackets. Hard70 is the leaderboard's", 13, INK2)
    c.text(pad, 74, "subset of the 70 tasks with the lowest average pass rate across 12 earlier models.", 13, INK2)
    for i, m in enumerate(solved):
        lx, ly = pad + (i % 2) * 330, 92 + (i // 2) * 20
        c.swatch(lx, ly, 12, colors[m])
        c.text(lx + 18, ly + 10.5, legend[m], 12.5, INK2)
    for v in range(0, 101, 20):
        c.vline(sx(v), top - 6, plot_bottom, AXIS if v == 0 else GRID)
        c.text(sx(v), plot_bottom + 18, f"{v}%", 12, MUTED, "center")
    y = top
    for g, _ in groups:
        c.text(pad + label_w, y + group_h / 2 + 4.5, g, 13, INK, "right", "bold")
        for m in solved:
            k, n = data[g][m]
            v = 100.0 * k / n
            c.bar(x0, y, sx(v) - x0, bar_h, colors[m])
            own = m in ours
            c.text(sx(v) + 6, y + bar_h / 2 + 4.5, f"{v:.1f}% ({k})", 12, INK if own else INK2, "left",
                   "bold" if own else "normal")
            y += bar_h + gap
        y += group_gap - gap
    c.text(pad, height - 26, "Sources: per-task results on swescience.github.io (9 Oct 2026); Fable 5.2 and Opus 5.5: this repository.", 11, MUTED)
    c.text(pad, height - 11, "Opus 5 was one of the 12 models used to select Hard70, which lowers its score there by construction; Astra and Fable 5.2 were not.", 11, MUTED)
    c.save("fig2-subsets")
    return height, data


if __name__ == "__main__":
    h1 = fig1()
    h2, data2 = fig2()
    print("fig1-leaderboard", W * SCALE, h1 * SCALE)
    print("fig2-subsets", W * SCALE, h2 * SCALE)
    for g, d in data2.items():
        print(g, {m: f"{k}/{n}" for m, (k, n) in d.items()})
