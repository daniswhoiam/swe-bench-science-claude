# analysis/

Scripts that reproduce every number in the README and in `fable-vs-paper.md`, from `results/` (Fable 5.2), `results/opus-5.5-max/` (Opus 5.5) and the leaderboard's own data. Run them from the repository root. Python 3.12+, standard library only, except `paradigm_bounds.py` (numpy, scipy >= 1.9) and `figures/make_figures.py` (matplotlib).

```bash
python -I analysis/fetch_inputs.py      # 1. leaderboard data, pinned to site commit f16153e and hash-checked
python -I analysis/summarise.py --check # 2. results/summary.json from results/ (no leaderboard data needed)
python -I analysis/summarise.py --run opus --check   #    results/opus-5.5-max/summary.json
python -I analysis/fable_vs_paper.py    # 3. comparison with the leaderboard (all sections)
python -I analysis/opus_vs_paper.py     #    Opus 5.5: against the leaderboard and the Fable run
python -I leaderboard-format/validate_entry.py
python -I leaderboard-format/validate_entry.py --run opus
python -I figures/make_figures.py       # needs matplotlib
python -I analysis/paradigm_bounds.py   # needs numpy and scipy
```

| File | Needs | Purpose |
|---|---|---|
| `fetch_inputs.py` | network (raw.githubusercontent.com) | downloads `task-matrix.json`, `benchmark.json`, `hard70.json`, `hard70-model-results.json` from `swescience/swescience.github.io` at commit `f16153e5c47c46b2f6f2ebf0aaefae34bdf8c8bd` into `data/leaderboard/` (git-ignored). Checks each file's SHA-256 against the pinned value, and the two main files' canonical-JSON SHA-256 against the snapshot this analysis was first run on. Also checks that `results/per-task.csv`'s `hard70` column equals the leaderboard's list |
| `common.py` | | loaders and small statistics helpers (exact McNemar, Wilson interval) |
| `summarise.py` | `results/` | headline aggregates; writes `results/summary.json` (`--check` compares instead; `--run opus` for `results/opus-5.5-max/summary.json`) |
| `opus_vs_paper.py` | `results/`, fetched data | Opus 5.5: Pass@1 with interval, subsets, time-limit sensitivity, per-task McNemar against the Fable run and the seven configurations with per-task results; prints only |
| `fable_vs_paper.py` | `results/`, fetched data | leaderboard metrics, per-task McNemar comparisons, slices, failure profile, cost, sensitivity; writes `out/chart-leaderboard.csv` and, into the git-ignored `out/local/`, tables that contain other configurations' per-task results |
| `paradigm_bounds.py` | fetched data, scipy | integer program: range of Fable's Issue/Expert/Engineering counts consistent with everything published; output committed as `out/paradigm_bounds-output.txt` |
| `extract_paper_domains.py` | the paper PDF, `pdftotext` | rebuilds `data/paper-domains.csv` from Table 5 of the paper |
| `tool_mix.py` | **the private trajectories** | behaviour counts per run; the committed output is `out/tool-mix.csv`. `--summary` prints medians from that file without the trajectories |
| `contamination_scan.py` | **the private agent records** | count-only network-attempt scan (`docs/network-scan.md`, `docs/network-scan-opus-5.5-max.md`); the committed outputs are `out/contamination-scan.csv` and `out/opus-5.5-max/contamination-scan.csv`. `--selftest` runs without any data |

## Committed outputs (`out/`)

| File | Content |
|---|---|
| `chart-leaderboard.csv` | 18 rows: the 17 published configurations (overall Pass@1, Hard70 Pass@1 where the leaderboard has one, tokens per task), quoted with their source, plus this run |
| `contamination-scan.csv` | per run: task ID, counts by category, reason codes (Fable 5.2) |
| `opus-5.5-max/contamination-scan.csv` | the same for Opus 5.5 |
| `tool-mix.csv` | per run: task ID, pass, behaviour counts and timings |
| `paradigm_bounds-output.txt` | console output of `paradigm_bounds.py` |

Not committed: `data/leaderboard/` (the site has no licence) and `out/local/` (per-task results of other configurations, regenerated after `fetch_inputs.py`).

`data/paper-domains.csv` holds the paper's domain label per task (arXiv 2608.19799, Table 5, CC BY 4.0), reproduced with attribution.
