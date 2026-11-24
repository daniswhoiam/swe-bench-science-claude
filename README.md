# Claude Fable 5.2 and Claude Opus 5.5 on SWE-bench Science

Two independent, unofficial runs on all 119 tasks of [SWE-bench Science](https://github.com/OpenMOSS/SWE-bench-Science), using the benchmark's own harness and an unmodified Claude Code:

- **Claude Fable 5.2 at xhigh effort**, with the output cap raised to 128,000 tokens. Submitted to the benchmark maintainers for review on 2026-11-17 ([OpenMOSS/SWE-bench-Science#4](https://github.com/OpenMOSS/SWE-bench-Science/issues/4)).
- **Claude Opus 5.5 at max effort**, the paper's headline condition, with every other setting at its default. Submitted to the benchmark maintainers for review on 2026-11-24 ([OpenMOSS/SWE-bench-Science#6](https://github.com/OpenMOSS/SWE-bench-Science/issues/6)).

Neither is an official leaderboard entry.

| | Pass@1 | Tasks solved |
|---|---|---|
| **Claude Fable 5.2, Claude Code 2.1.293, xhigh (this repository)** | **63.03%** (Wilson 95% CI 54.1-71.2) | **75 / 119** |
| **Claude Opus 5.5, Claude Code 2.1.293, max (this repository)** | **59.66%** (Wilson 95% CI 50.7-68.0) | **71 / 119** |
| GPT-6 Astra, Codex, max (leaderboard, 2026-10-09) | 50.42% | 60 / 119 |
| Claude Opus 5, Claude Code, max (leaderboard, 2026-10-09) | 47.90% | 57 / 119 |

Leaderboard-style metrics:

| | Fable 5.2, xhigh | Opus 5.5, max |
|---|---|---|
| Public macro | 99.16% | 100.00% |
| Private macro | 85.26% | 85.78% |
| Hard70 | 29/70 (41.4%) | 24/70 (34.3%) |
| The other 49 tasks | 46/49 | 47/49 |
| Default 96-task selection | 60/96 | 57/96 |
| 23 restricted-licence tasks | 15/23 | 14/23 |

Fail2Pass, Pass2Pass and the Issue/Expert/Engineering columns cannot be computed from the data in this repository (see [What is not computed](#what-is-not-computed)).

![Pass@1 on SWE-bench Science for 19 configurations: Claude Fable 5.2 (this repository, xhigh) 63.0%; Claude Opus 5.5 (this repository, max) 59.7%; GPT-6 Astra (Codex, max) 50.4%; Claude Opus 5 (Claude Code, max) 47.9%; the other 15 leaderboard configurations from 40.3% down to 7.6%.](figures/fig1-leaderboard.png)

![Pass@1 by subset for both runs and the leaderboard's top two configurations. All 119 tasks: Fable 5.2 63.0% (75), Opus 5.5 59.7% (71), GPT-6 Astra 50.4% (60), Claude Opus 5 47.9% (57). Hard70: 41.4% (29), 34.3% (24), 30.0% (21), 21.4% (15). Other 49 tasks: 93.9% (46), 95.9% (47), 79.6% (39), 85.7% (42).](figures/fig2-subsets.png)

## Contents

The Fable 5.2 files are at the top level of each directory. The Opus 5.5 files have the same names and formats, in an `opus-5.5-max/` subfolder.

- `results/per-task.csv`: one row per task with outcome, public/private pass counts, time, turns, tokens, list cost, patch size and checksum, network mode. The data dictionary is in `results/README.md`.
- `results/runs.jsonl`: the same runs as structured records (sanitised). `results/summary.json`: headline aggregates.
- `leaderboard-format/`: the per-task results in the leaderboard's own `task-matrix.json`, `benchmark.json` and `hard70-model-results.json` schemas, plus a validator.
- `provenance/`: exact command, versions, image digests, per-trial network policy, run order, a dated run log and the pre-release scan.
- `analysis/`: scripts that reproduce every number in this README. `analysis/fable_vs_paper.py` and `analysis/opus_vs_paper.py` print the comparisons with the leaderboard; `analysis/fable-vs-paper.md` is a longer written analysis of the Fable 5.2 run.
- `docs/network-scan.md` (Fable 5.2) and `docs/network-scan-opus-5.5-max.md` (Opus 5.5): the count-only scans of the agent records for network or download attempts.
- `figures/`: the two figures above and the script that draws them.
- `harness/`: the driver (`--config fable-xhigh` or `--config opus-max`), the environment class and the record builder used for the runs.

**Not included, on purpose:**

- Task content (instructions, source snapshots, supplied materials).
- Hidden-test code or any verifier output beyond pass counts.
- Agent transcripts and patches.

Some tasks carry restricted licences (GPL family, non-commercial, unclear redistribution rights), and publishing working patches would put benchmark solutions online. The SHA-256 of every patch is listed in `results/artefact-checksums.csv` and `results/opus-5.5-max/artefact-checksums.csv`, and the patches and transcripts are available to the benchmark maintainers for verification.

## Configuration

Both runs share everything except the rows marked *per run*.

| Item | Value |
|---|---|
| Model *(per run)* | Fable 5.2: `anthropic/claude-fable-5-2`; Claude Code reports `claude-fable-5-2` in all 119 runs and no other model in its 116 usage reports. Opus 5.5: `anthropic/claude-opus-5-5`; reported as `claude-opus-5-5` in all 119 runs and no other model in its 115 usage reports |
| Agent | Claude Code 2.1.293, the built-in `claude-code` agent of `datacurve-pier==0.3.0`. The task's `instruction.md` is the only prompt. No extra tools, hooks or instructions |
| Effort *(per run)* | Fable 5.2: `reasoning_effort=xhigh`. Opus 5.5: `reasoning_effort=max` |
| Output cap *(per run)* | Fable 5.2: `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000`. Opus 5.5: not set; Claude Code's default for Opus 5.5 (it reports 128,000) |
| Limits | 5400 s agent, 1800 s verifier, 2 CPUs and 8 GB per container (from each `task.toml`; unchanged) |
| Network | Agent: `isolated-allowlist`, only `api.anthropic.com`. Verifier: `none`. Checked on every trial |
| Environment class | the benchmark's `ScienceBenchDocker`, with one change: an Ubuntu mirror for building the egress-proxy image (`harness/environment.py`) |
| Dataset | HF `OpenMOSS-Team/SWE-bench-Science` revision `997408298e8e4d09978b1120b95c4540d1a71bcb`; `manifests/tasks.jsonl` sha256 `bcada90a99fcfd88e67ff4faf38af8ad3dad354b32a5a904a75d378e29ca8d4c`; all 119 tasks materialised with `--allow-restricted-licenses` |
| Attempts | one scored attempt per task; Pier `--n-attempts 1 --max-retries 0` |
| Order | seeded random shuffle of the 119 tasks (seed 20261111; `provenance/run-order.json`), the same for both runs |
| Hardware *(per run)* | native linux/amd64, Ubuntu 24.04.5. Fable 5.2, server A: Intel Core i9-13900, 64 GB, Docker 29.9.3, 7 tasks at a time, 92 tasks (13-14 Nov 2026); server B: Intel Core i5-12500, 64 GB, Docker 29.10.0, 6 at a time, 27 tasks (17 Nov 2026). Opus 5.5, server C: Intel Core i5-12500, 64 GB, Docker 29.10.0, 6 at a time, all 119 tasks (23-24 Nov 2026) |

The exact per-task commands are in `provenance/pier-command.txt` (Fable 5.2) and `provenance/opus-5.5-max/pier-command.txt` (Opus 5.5); more detail in `provenance/environment.md`.

## Differences from the paper's setup

| | Paper / benchmark repository | Fable 5.2 | Opus 5.5 |
|---|---|---|---|
| Effort | max | **xhigh** (see below) | max |
| Output-token cap | not reported (Claude Code's default depends on the model: 32,000 for Fable 5.2, 128,000 for Opus 5.5 in 2.1.293) | **128,000** | default (128,000) |
| Claude Code version | not reported (2.1.221 for one leaderboard entry, per the maintainers) | 2.1.293 | 2.1.293 |
| Runner | `scripts/run_batch.py` or `pier run` | `pier run` per task through `harness/run_fable.py`, same network policy | `pier run` per task through `harness/run_fable.py`, same network policy |
| Hardware | not reported | two native x86 servers (above) | one native x86 server (above) |
| Interrupted sessions | not reported | set aside and rerun from scratch (see [Run integrity](#run-integrity)) | none occurred |
| Time-limit runs | scored on workspace (Pier) | same: 3 runs (062, 107, 108), all pass | same: 4 runs (001, 014, 033, 040), 001 passes |

**Effort.** Opus 5.5 ran at max, the paper's setting. The Fable 5.2 run also started at max, but after 47 minutes none of the first seven tasks had finished, and it was switched to xhigh for cost and time. The switch was made before any max-effort outcome existed.

**Output cap.** In a Fable 5.2 test run at Claude Code's default cap, a max-effort session ended with an API error when a response exceeded 32,000 output tokens, so the cap was raised to 128,000 for the Fable 5.2 run. Opus 5.5 kept its default: in its session files, 56 single responses exceeded 32,000 output tokens (the largest 100,586) in 45 runs, and none ended in an error. No other agent environment variable was set in either run.

## How scoring works

- Each patch is evaluated by the benchmark's own verifier image and grader in a separate container without network access.
- A task counts as solved (Pass@1 = 1) when every private test passes. The grader's reward also requires the public reproduction to pass; in both runs the two coincide on all 119 tasks.
- With one attempt per task, Pass@1 is the mean of 119 binary rewards. The 95% intervals are Wilson intervals treating the 119 tasks as a sample. They cover task sampling only; run-to-run variation was not measured for either model.
- **Time limit.** A run that hits the 90-minute agent limit is scored on its final workspace, as Pier does.
- **Verifier timeout.** A run whose verifier produces no result counts as a failure. In the leaderboard format it is recorded as 0 of the leaderboard's test totals, the convention the leaderboard uses for an evaluation that produced nothing.
- **Public and private macro values** follow the paper's definition: the mean over tasks of the share of tests passed.

| | Fable 5.2, xhigh | Opus 5.5, max |
|---|---|---|
| Pass@1 | 75/119 = 63.03% (Wilson 95% 54.1-71.2) | 71/119 = 59.66% (Wilson 95% 50.7-68.0) |
| Public reproduction passes | 118 of 119 | 119 of 119 |
| Runs that hit the time limit | 3 (062, 107, 108), all pass | 4 (001, 014, 033, 040), 001 passes |
| Pass@1 with those runs scored as failures | 72/119 = 60.5% | 70/119 = 58.8% |
| Verifier timeouts | 1: on task 002 the agent finished normally, but the verifier ran 60 minutes without a result | none; every run has a verifier result |

### What is not computed

- **Fail2Pass / Pass2Pass.** These need per-test results before and after the patch. The records of both runs hold pass counts only, and no per-test verifier output was opened. The maintainers can compute them by re-evaluating the patches.
- **Issue / Expert / Engineering Pass@1.** The task-to-paradigm labels are not published, so neither run can be split by paradigm. `analysis/paradigm_bounds.py` shows, for the Fable 5.2 result, that the split is not identifiable from public data.
- **Task 032.** In both runs the verifier image collects 6 private tests, while the leaderboard lists 21. The task passes either way.

## Comparison with the leaderboard

The leaderboard publishes per-task results for seven configurations (<https://swescience.github.io/task-matrix/gradient/>). `analysis/fetch_inputs.py` downloads them from the site repository at commit `f16153e5c47c46b2f6f2ebf0aaefae34bdf8c8bd`, and `analysis/fable_vs_paper.py` and `analysis/opus_vs_paper.py` pair them with each run task by task. The table compares each run with the leaderboard's top two configurations: the tasks only that run solves against the tasks only the leaderboard configuration solves, with an exact McNemar test.

| Against | Fable 5.2: only Fable 5.2 / only the other | p | Opus 5.5: only Opus 5.5 / only the other | p |
|---|---|---|---|---|
| GPT-6 Astra (max, Codex), all 119 tasks | 20 / 5 | 0.0041 | 16 / 5 | 0.027 |
| Claude Opus 5 (max, Claude Code), all 119 tasks | 20 / 2 | 0.00012 | 17 / 3 | 0.0026 |
| GPT-6 Astra, all 119 tasks; Fable 5.2 / Opus 5.5 time-limit runs scored as failures | 18 / 6 | 0.023 | 15 / 5 | 0.041 |
| Claude Opus 5, all 119 tasks; Fable 5.2 / Opus 5.5 time-limit runs scored as failures | 20 / 5 | 0.0041 | 16 / 3 | 0.0044 |
| GPT-6 Astra, Hard70 only | 12 / 4 | 0.077 | 7 / 4 | 0.55 |
| Claude Opus 5, Hard70 only | 16 / 2 | 0.0013 | 12 / 3 | 0.035 |

- Of the 35 tasks that none of the seven configurations solves, Fable 5.2 solves 6 (036, 065, 068, 090, 097, 113) and Opus 5.5 solves 3 (001, 068, 097). Opus 5.5's 001 is one of its time-limit runs.
- Claude Opus 5 → Opus 5.5 is the closest pairing with the leaderboard: the same harness (Claude Code) and effort (max). It still differs in Claude Code version, output cap and hardware, which are not all reported for the leaderboard run.
- Claude Opus 5 was one of the 12 models used to select Hard70, which lowers its Hard70 score by construction. GPT-6 Astra and Fable 5.2 were not.

These are not matched comparisons. The leaderboard runs were made by the benchmark authors at max effort, with Claude Code or Codex versions, output caps and hardware that are not all reported. The paired test controls for task difficulty, not for those conditions. A longer analysis of the Fable 5.2 run is in `analysis/fable-vs-paper.md`.

### Fable 5.2 and Opus 5.5 compared

The two runs solve 67 tasks in common. Fable 5.2 alone solves 8 and Opus 5.5 alone solves 4 (exact McNemar p = 0.39, not significant); on Hard70 the split is 8 to 3 (p = 0.23). Together they solve 79 of the 119 tasks. The comparison is matched in Claude Code version, task order and benchmark copy, but not in effort (xhigh vs max), output-cap setting, hardware or date.

## Run integrity

Both runs were checked the same way:

- **Network.** Every trial ran with the benchmark's isolated network policy: the agent could reach only `api.anthropic.com` through the proxy, and the verifier had no network. The policy files are summarised per task in `provenance/per-task-provenance.jsonl` and `provenance/opus-5.5-max/per-task-provenance.jsonl`. The agent records of all 119 runs of each model were scanned for network or download attempts by count only, with patterns fixed before the first scan and unchanged since (`analysis/contamination_scan.py`; `docs/network-scan.md`, `docs/network-scan-opus-5.5-max.md`). The scan cannot see network calls made from inside scripts the agent ran from files, except through their printed output. Most tasks belong to a held-out research set, so in both runs their transcripts were scanned mechanically without being read; the flagged runs are listed by task ID with their counts, for the maintainers to inspect.
- **Usage limits and interruptions.** Both runs used a Claude subscription. A session cut off by the usage limit, or interrupted by a server shutdown, is discarded and the task rerun from scratch; such sessions are never scored and are not part of this repository. The rule looks only at the session's error text, never at the verifier result (`harness/run_fable.py`, `session_error` and `do_entry`). Timelines: `provenance/run-log.md` and `provenance/opus-5.5-max/run-log.md`.
- **Credentials.** Every job folder and Pier log was scanned for the OAuth token prefix (`token_prefix_hits` in `runs.jsonl`). The published files were scanned again before release (`provenance/release-scan.md`).
- **Hidden tests.** No hidden-test source or verifier output (`test-stdout.txt`, `junit.xml`, `ctrf.json`, `run.log`) was opened at any point. Only the count file `reward.json` was read.

| | Fable 5.2 | Opus 5.5 |
|---|---|---|
| Web-search requests reported by Claude Code | 0 in the 116 runs that report usage (the 3 time-limit runs end without a report) | 0 in the 115 runs that report usage (the 4 time-limit runs end without a report) |
| Web-fetch or web-search tool calls (available in every run) | 0 | 0 |
| curl, wget, ssh, system package managers | 0 | 0 |
| `pip download` | 20 calls in 19 runs, every result a blocked-network error | 12 calls in 12 runs, every result a blocked-network error |
| Other shell network commands | 3 non-local `pip install`/`uv` calls in one run (018), no blocked or success signal in their results | 1 `git clone` (071), of the agent's own working directory; no network request |
| Network code or URL run inline in Bash | 7 calls in 6 runs, no blocked or success signal in their results | 1 call with a PyPI URL (090), blocked |
| Network attempts whose result shows a successful download | 0 | 0 |
| Flagged runs (of them never read) | 26 (14) | 14 (8) |
| Usage limit | hit twice; the sessions it cut off, and the runs interrupted when server A was shut down, were discarded and the tasks rerun | never reached; no session was set aside or rerun |
| Token-prefix hits | 0 in all 119 job folders | 0 in all 119 job folders |

In the Opus 5.5 run, the subscription's usage meter came close to its limit late in the pass, so new task starts were paused for 86 minutes, until the meter had reset and the six running tasks had finished. Running tasks were not interrupted, and the pause was decided on the meter, not on results. After the Opus 5.5 data was copied and checked against the server, the server was wiped, and a search of its filesystem found no file containing the token prefix.

## Caveats

- One attempt per task for each model. A rerun could move either total by a few tasks.
- Neither run is a matched comparison with the leaderboard (effort, Claude Code version, output cap, hardware).
- List costs are Claude Code's own estimates at API list prices, not what was paid (a subscription was used). In both runs the per-task table uses Claude Code's total for cost and Pier's counts for tokens.

Fable 5.2:

- xhigh rather than the paper's max effort; output cap raised to 128k. Claude Code's usage report lists `maxOutputTokens: 32000` in every run, but that field does not reflect the effective cap: in the 41 runs whose session files were inspected, 18 single responses exceeded 32,000 output tokens (the largest 91,727), which the default cap would have ended with an API error. The raised cap was therefore in effect and was used.
- Two servers, run 3-4 days apart. The order was random, so the split is not tied to task difficulty (server A 56/92, server B 19/27).
- Three time-limit runs are scored on workspace state, and one verifier timeout is scored as a failure (see [How scoring works](#how-scoring-works)).
- List cost $488 in total, $4.21 per run, for the 116 runs that report it. Mean agent time 38.3 minutes per task (median 35.7).

Opus 5.5:

- One server, one pass (23-24 Nov 2026).
- Four time-limit runs are scored on workspace state (see [How scoring works](#how-scoring-works)).
- List cost $927 in total, $8.06 per run, for the 115 runs that report it. Mean agent time 34.0 minutes per task (median 27.5). For two runs (037, 081), Pier's cost and token counts are lower than Claude Code's session total, because background subagents made the session emit several result events.

## Reproduce

Requirements: a native linux/amd64 host with Docker Engine 28+, Python 3.12+, about 2 CPUs and 8 GB RAM per concurrent task, and an Anthropic credential that can use `claude-fable-5-2` or `claude-opus-5-5`.

```bash
# 1. Harness and dataset (pinned)
python3.12 -m venv .venv && .venv/bin/pip install -r harness/requirements.txt   # datacurve-pier==0.3.0
hf download OpenMOSS-Team/SWE-bench-Science --repo-type dataset \
  --revision 997408298e8e4d09978b1120b95c4540d1a71bcb --local-dir swe-bench-science
(cd swe-bench-science && python3 scripts/materialize.py --allow-restricted-licenses \
  --output tasks-selected-all --force)    # restricted-licence opt-in: check that your use is permitted

# 2. Credentials, outside the repository
mkdir -p ~/.config/swe-bench-science && chmod 700 ~/.config/swe-bench-science
cp swe-bench-science/profiles/claude.env.example ~/.config/swe-bench-science/claude.env
# set CLAUDE_CODE_OAUTH_TOKEN (a subscription token, as used for both runs) or ANTHROPIC_AUTH_TOKEN
chmod 600 ~/.config/swe-bench-science/claude.env

# 3. Run all 119 tasks in the published order (--dry-run prints the order and one Pier command)
#    Fable 5.2 at xhigh:
.venv/bin/python -m harness.run_fable --config fable-xhigh --bench swe-bench-science --tasks-dir tasks-selected-all \
  --run-dir runs/fable-xhigh --order provenance/run-order.json --concurrency 7
#    Opus 5.5 at max:
.venv/bin/python -m harness.run_fable --config opus-max --bench swe-bench-science --tasks-dir tasks-selected-all \
  --run-dir runs/opus-max --order provenance/opus-5.5-max/run-order.json --concurrency 6

# 4. Records and analysis
.venv/bin/python -m harness.record runs/fable-xhigh/jobs --tasks-dir swe-bench-science/tasks-selected-all \
  --out runs.jsonl --csv runs-summary.csv               # likewise runs/opus-max/jobs for Opus 5.5
.venv/bin/python -I analysis/fetch_inputs.py
.venv/bin/python -I analysis/fable_vs_paper.py
.venv/bin/python -I analysis/opus_vs_paper.py
```

To check the published numbers without rerunning anything, only the last three commands are needed (see `analysis/README.md`). `analysis/tool_mix.py` and `analysis/contamination_scan.py` need the agent transcripts, which are not published; their outputs are committed in `analysis/out/`.

## Licence and attribution

- Code (`harness/`, `analysis/*.py`, `figures/make_figures.py`, `leaderboard-format/validate_entry.py`): MIT, see `LICENSE`.
- Results, provenance, figures and documentation: CC BY 4.0, see `LICENSE-DATA.md`.
- Third-party inputs keep their own terms (`NOTICE.md`):
  - Task metadata columns from the SWE-bench Science dataset (MIT, OpenMOSS).
  - Domain labels from Table 5 of the paper (arXiv 2608.19799, CC BY 4.0).
  - Leaderboard figures quoted with their source. The leaderboard's data files are downloaded by `analysis/fetch_inputs.py`, not redistributed.
- SWE-bench Science task content, images and tests belong to their respective owners and are not part of this repository.

Please cite the benchmark:

```bibtex
@article{xu2026swebenchscience,
  title   = {SWE-bench Science: Can Coding Agents Resolve Engineering Tasks in Science?},
  author  = {Xu, Zhipeng and Lu, Jiahao and Zheng, Yining and Wang, Yuxin and Qiu, Xipeng},
  journal = {arXiv preprint arXiv:2608.19799},
  year    = {2026}
}
```

To cite these runs, see `CITATION.cff`.

## Disclosure

Independent runs by Daniil Belazovschi (daniswhoiam). I am not affiliated with Anthropic or with the SWE-bench Science authors. I used both models through a Claude subscription and rented the servers myself.

Contact: [GitHub issues on this repository](https://github.com/daniswhoiam/swe-bench-science-claude/issues).

## Changelog

- v1.1.1 (2026-11-24): documentation only. The README presents both runs side by side, and the comparison table adds the Hard70 and time-limit rows for Fable 5.2 that `analysis/fable_vs_paper.py` already printed, and the Fable 5.2 vs Opus 5.5 Hard70 split that `analysis/opus_vs_paper.py` already printed. The two subset figures are merged into `fig2-subsets.png` (both runs and the leaderboard's top two); `fig3-opus-subsets.png` is removed. Wording in `results/README.md`, `leaderboard-format/README.md`, `analysis/README.md`, `provenance/` and `docs/` follows the same pattern. No data file changed; the subset figure was redrawn.
- v1.1 (2026-11-24): Claude Opus 5.5, max, 119 tasks, in `opus-5.5-max/` subfolders, with its network scan (`docs/network-scan-opus-5.5-max.md`), comparison script (`analysis/opus_vs_paper.py`) and a new figure (`fig3`). The Opus 5.5 run was made at max, the paper's headline condition, instead of the xhigh run planned in v1.0. Figure 1 now includes it. `harness/run_fable.py` takes `--config`; `summarise.py`, `validate_entry.py` and `contamination_scan.py` handle both runs. The repository was renamed from `swe-bench-science-fable-5.2` (old links redirect). Fable 5.2 files unchanged, except one correction: the credential variable is `CLAUDE_CODE_OAUTH_TOKEN`, not `ANTHROPIC_AUTH_TOKEN` (`provenance/environment.md`, `provenance/pier-command.txt`).
- v1.0 (2026-11-17): Claude Fable 5.2, xhigh, 119 tasks.
