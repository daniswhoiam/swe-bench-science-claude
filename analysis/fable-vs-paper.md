# Claude Fable 5.2 on SWE-bench Science: comparison with the paper and the leaderboard

Run analysed: Claude Fable 5.2 (`anthropic/claude-fable-5-2`), built-in Claude Code 2.1.293 agent in Pier 0.3.0, effort xhigh, `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000`, 90-minute agent limit, native x86, one attempt on each of the 119 tasks. Result: **75/119 = 63.0% Pass@1**.

Sources: the paper (arXiv 2608.19799v2, CC BY 4.0), the leaderboard at <https://swescience.github.io> (updated 9 Oct 2026, 17 configurations) and its per-task results page <https://swescience.github.io/task-matrix/gradient/>, which publishes per-task public and private pass counts for the 7 configurations above Nex N2. The leaderboard data is downloaded by `analysis/fetch_inputs.py` from the site repository at commit `f16153e`. Every number below is printed by `analysis/fable_vs_paper.py`, `analysis/summarise.py`, `analysis/paradigm_bounds.py` or `analysis/tool_mix.py --summary` from this repository's `results/` and that download.

Only count-level data is used: the verifier's pass counts per task, never per-test results, hidden-test source or verifier logs.

---

## Main findings

1. **Fable leads the published leaderboard on the same 119 tasks, and the gap holds up in a paired test.** Fable passes 75/119 (63.0%), against 60/119 (50.4%) for GPT-6 Astra (max, Codex) and 57/119 (47.9%) for Claude Opus 5 (max, Claude Code). Task by task, Fable solves 20 tasks that Astra misses and misses 5 that Astra solves (exact McNemar p = 0.004). Against Opus 5 the split is 20 to 2 (p = 0.0001). Paired-bootstrap 95% intervals for the gap: +5.0 to +21.0 points over Astra, +8.4 to +22.7 over Opus 5.
2. **Fable leads on both halves of the benchmark.** On the leaderboard's Hard70 subset Fable passes 29/70 (41.4%), against 21/70 (30.0%) for Astra and 15/70 (21.4%) for Opus 5. On the other 49 tasks it passes 46/49 (93.9%), against 39 and 42. The lead over Astra is about the same size on both (+11.4 and +14.3 points); against Opus 5 it is concentrated in Hard70.
3. **Fable solves 6 of the 35 tasks that none of the seven configurations with per-task results solves** (036, 065, 068, 090, 097, 113). Only one task that at least five of those seven solve is a Fable failure: 115, where Fable passed 93 of 97 checks.
4. **Against GPT-6 Astra, the lead comes from finishing tasks, not from more partial credit.** The mean share of private checks passed is close (Private score 85.3% against 83.2%). Of the 20 tasks only Fable solves, Astra missed exactly one check on 12 and two checks on 4. Astra has 22 one-check misses, Fable 11, and Astra solves none of Fable's 11.
5. **Token use.** Fable uses fewer input tokens per task than Opus 5 (max) and more output tokens: 5.3M against 7.0M input (94% of Fable's are cache reads), 0.166M against 0.110M output. At list prices this is $13.74 per task (corrected in v1.2: Claude Code's own estimate, $4.21, has no price basis for Fable 5.2; see the README, "Claude Code version"). Over the 18 configurations, Pass@1 is not positively related to token use (Spearman rank correlation −0.32 with input tokens, −0.21 with output tokens).
6. **Fable's failures look like missing work, not broken code.** 43 of its 44 failures pass the public reproduction, and 41 of the 44 are Hard70 tasks. Passing and failing runs show the same effort (median 62.5 against 63 turns, 34 against 37 minutes, 23 against 20.5 Python executions).

---

## 1. Leaderboard-comparable metrics

**Definitions (paper Sec. 5, Table 2 caption).**

- *PublicScore* is the mean over a task's public test cases. *PrivateScore* is the same over its private cases.
- *Fail2Pass* is the fraction of private tests that failed before the repair and pass after it. *Pass2Pass* is the fraction of previously passing private tests that still pass.
- *Pass@1* is 1 only if every applicable private test passes.
- All aggregates are "task-level means over the common 119 tasks", i.e. macro averages.
- The Issue, Expert and Engineering columns are Pass@1 within the paradigm. The paradigms have 52, 49 and 18 tasks (paper Sec. 3).

**Check of the definitions.** Macro means of the published per-task counts reproduce the published Public, Private and Overall values exactly (to 0.01) for 6 of the 7 configurations with per-task data. Micro averages do not; for example, Opus 5's private micro average is 81.21 against the published 75.11. The exception is Kimi-K3: its aggregate Public (98.32) and Private (66.34) values imply a different record for task 061 from the one in the matrix (matrix 0/1 and 0/1, giving 97.48 and 66.13). Its Overall value matches.

**Fable under the same definitions.**

| Metric | Fable 5.2 (xhigh) | GPT-6 Astra (max) | Claude Opus 5 (max) | Reproducible? |
|---|---|---|---|---|
| Public | 99.16% (100.00% without 002) | 100.00 | 96.64 | yes |
| Private | 85.26% (85.98% without 002) | 83.18 | 75.11 | yes |
| Fail2Pass | not computable | 80.11 | 68.60 | **no** |
| Pass2Pass | not computable | 95.95 | 97.37 | **no** |
| Overall Pass@1 | **63.03%** (75/119; Wilson 95% 54.1–71.2) | 50.42 | 47.90 | yes |
| Issue / Expert / Engineering | not identifiable (see below) | 46.15 / 57.14 / 44.44 | 38.46 / 65.31 / 27.78 | **no** |

Notes:

- **Task 002**: the agent finished normally, but the verifier ran 60 minutes without a result. It is scored as a failure. For Public and Private it is scored 0 of the leaderboard's totals, which is how the leaderboard records an evaluation that produced nothing (Kimi-K3 on 061).
- **Public reproduction**: passes on 118 of 119 tasks (all but 002).
- **Denominators**: our private-test totals match the leaderboard's on 117 of the 118 tasks with a result. On task 032 our verifier image collects 6 private tests, against 21 on the leaderboard. 032 passes either way.
- **Fail2Pass and Pass2Pass** need per-test results before and after the patch. This run's records hold pass counts only, and no per-test verifier output was opened. The maintainers can compute them by re-evaluating the patches.
- **The paradigm labels are not published.** We searched the paper, the dataset README, `tasks.csv`, `manifests/tasks.jsonl`, the task bundles (excluding `tests/`), the GitHub docs and the leaderboard's data. None of them says which task belongs to which paradigm.
  - We therefore asked which assignments are consistent with what is published: the paradigm sizes, the seven configurations' per-paradigm Pass@1 values, and their per-task results. Among all such assignments (integer program, `paradigm_bounds.py`, output in `out/paradigm_bounds-output.txt`), Fable's count can be anywhere in these ranges:
    - Issue: 19–40 of 52 (36.5–76.9%)
    - Expert: 30–48 of 49 (61.2–98.0%)
    - Engineering: 4–18 of 18 (22.2–100%)
  - The constraints force no single task into a paradigm. The paradigm split of Fable's result cannot be identified from public data. **Do not report Issue, Expert or Engineering numbers for Fable.**
- Two smaller inconsistencies:
  - The paper's DeepSeek-V4-Pro row (42.02% overall) differs from the leaderboard's (39.50%). The per-task data matches the leaderboard version.
  - Fable's Wilson interval treats the 119 tasks as a sample of possible tasks.

## 2. Per-task comparison with the published configurations

**Data.** The leaderboard's task-matrix page publishes per-task public and private pass counts and Pass@1 for 7 configurations: GPT-6 Astra, Opus 5, GPT-5.6-sol, DeepSeek-V4-Pro, Kimi-K3, GLM-5.2 and Qwen3.8-27B. No per-task data exists for the other 10 configurations, all of which score 24.4% or less.

| Configuration | Overall | Both pass | Fable only | Config only | Neither | Exact McNemar p |
|---|---|---|---|---|---|---|
| GPT-6 Astra (max, Codex) | 60/119 | 55 | 20 | 5 | 39 | 0.0041 |
| Claude Opus 5 (max, Claude Code) | 57/119 | 55 | 20 | 2 | 42 | 0.00012 |
| GPT-5.6-sol (max, Codex) | 48/119 | 43 | 32 | 5 | 39 | 7e-6 |
| DeepSeek-V4-Pro (max, Claude Code) | 47/119 | 41 | 34 | 6 | 38 | 8e-6 |
| Kimi-K3 (max, Kimi Code) | 42/119 | 39 | 36 | 3 | 41 | 4e-8 |
| GLM-5.2 (max, Codex) | 38/119 | 33 | 42 | 5 | 39 | 3e-8 |
| Qwen3.8-27B (xhigh, Claude Code) | 35/119 | 32 | 43 | 3 | 41 | 5e-10 |

- The two main comparisons (Astra and Opus 5) stay significant after Bonferroni correction for two tests (0.004 < 0.025).
- If the three runs that hit the 90-minute limit had been scored as failures instead of on workspace state, Fable would have 72/119 = 60.5%. It would still lead: 18 to 6 against Astra (p = 0.023), 20 to 5 against Opus 5 (p = 0.004).
- The 5 tasks Astra solves and Fable fails are 002 (the verifier timeout), 005, 041, 049 and 115. The 2 tasks Opus 5 solves and Fable fails are 044 and 119.
- Of the 35 tasks that none of the seven configurations solves, Fable solves 6: 036, 065, 068, 090, 097 and 113.
- The union of the seven configurations covers 84/119 tasks; adding Fable raises it to 90/119. Fable fails 15 tasks that at least one of the seven solves.
- Fable against how many of the seven solve each task:

| Configs passing (of 7) | Tasks | Fable | Opus 5 | Astra |
|---|---|---|---|---|
| 0 | 35 | 6 | 0 | 0 |
| 1 | 18 | 9 | 4 | 9 |
| 2 | 10 | 9 | 6 | 7 |
| 3 | 10 | 7 | 6 | 5 |
| 4 | 9 | 8 | 5 | 6 |
| 5 | 12 | 11 | 11 | 8 |
| 6 | 12 | 12 | 12 | 12 |
| 7 | 13 | 13 | 13 | 13 |

Caveat: one attempt per task on each side. The leaderboard runs were made by the authors with an unreported Claude Code or Codex version, hardware and output cap. A paired test controls for task difficulty, not for those conditions.

## 3. Where the lead comes from

Counts are passes out of the number of tasks in the slice. Many cells are small.

**Hard70** (leaderboard definition: the 70 tasks with the lowest mean pass rate over 12 earlier models)

| Slice | Tasks | Fable | Astra | Opus 5 | GPT-5.6-sol | DeepSeek-V4-Pro |
|---|---|---|---|---|---|---|
| Hard70 | 70 | 29 (41.4%) | 21 (30.0%) | 15 (21.4%) | 10 | 12 |
| Other 49 | 49 | 46 (93.9%) | 39 (79.6%) | 42 (85.7%) | 38 | 35 |

Paired comparisons within each subset:

- Hard70, Fable against Astra: 12 to 4 (p = 0.077). Against Opus 5: 16 to 2 (p = 0.0013).
- Other 49, against Astra: 8 to 1 (p = 0.039). Against Opus 5: 4 to 0 (p = 0.12).

The lead over Astra is spread across both subsets. Against Opus 5 it is concentrated in Hard70. Opus 5 was one of the twelve models used to select Hard70, which lowers its score there by construction; Astra and Fable were not.

**Paper domains** (the 20 domains from paper Table 5, `data/paper-domains.csv`; the counts match Table 4 exactly)

| Domain | Tasks | Fable | Astra | Opus 5 |
|---|---|---|---|---|
| Chemistry | 24 | 14 | 13 | 13 |
| Materials Science & Eng. | 16 | 7 | 4 | 5 |
| Biology | 13 | 11 | 8 | 8 |
| Biomedical Eng. | 12 | 10 | 8 | 9 |
| Physics | 11 | 5 | 2 | 3 |
| Astronomy | 7 | 4 | 3 | 3 |
| Mathematics | 7 | 6 | 6 | 5 |
| Atmospheric Science | 5 | 4 | 4 | 3 |
| Civil Engineering | 5 | 3 | 4 | 3 |
| 11 smaller domains | 19 | 11 | 8 | 5 |

Fable is at or above Opus 5 in all 20 domains (strictly above in 14). Against Astra it is above in 9, equal in 10 and below in 1 (Civil Engineering, 3 against 4). The lead is broad. No domain cell supports a domain-specific claim.

**Other slices**

| Slice | Tasks | Fable | Astra | Opus 5 |
|---|---|---|---|---|
| Python | 103 | 64 | 51 | 49 |
| Not pure Python (C, C++, Fortran, MATLAB/Octave, mixed) | 16 | 11 | 9 | 8 |
| Third-party materials supplied (`material_license` set) | 62 | 38 (61%) | 28 (45%) | 25 (40%) |
| No materials | 57 | 37 (65%) | 32 (56%) | 32 (56%) |
| `science_knowledge_ablation` subset | 91 | 58 (64%) | 46 (51%) | 43 (47%) |
| Not in the ablation subset | 28 | 17 (61%) | 14 (50%) | 14 (50%) |
| Default 96 (unrestricted licences) | 96 | 60 | 50 | 46 |
| Restricted 23 | 23 | 15 | 10 | 11 |
| More than 20 private checks | 11 | 8 | 10 | 8 |

Readings:

- **Supplied materials.** The published configurations do worse on tasks that come with supplied scientific materials (Astra 45% against 56%, Opus 5 40% against 56%). Fable shows a smaller drop (61% against 65%). This is descriptive only, about 60 tasks per cell, and has no causal meaning.
- **Large test suites.** On the 11 tasks with more than 20 private checks, Fable (8) is behind Astra (10).
- **Hardware.** The first server passed 56 of its 92 tasks, the second 19 of its 27. Of the second server's tasks, 17 were Hard70. There is no sign that the slower second server hurt.

## 4. Failure profile

| Configuration | Failures | Mean share of private checks passed (failures only) | Missed exactly 1 | Missed 2 | Missed ≥5 | 0 passed |
|---|---|---|---|---|---|---|
| **Fable** | 44 | 0.601 | 11 | 10 | 13 | 1 (002, no result) |
| GPT-6 Astra | 59 | 0.661 | 22 | 14 | 12 | 0 |
| Opus 5 | 62 | 0.522 | 13 | 10 | 21 | 6 |
| GPT-5.6-sol | 71 | 0.591 | 25 | 8 | 21 | 3 |
| DeepSeek-V4-Pro | 72 | 0.529 | 17 | 12 | 26 | 5 |

Over all 119 tasks, the mean share of private checks passed is: Fable 85.3%, Astra 83.2%, GPT-5.6-sol 75.6%, Opus 5 75.1%.

- **Near misses.** Fable's missed-check counts are: 1 check (11 failures), 2 (10), 3 (5), 4 (5), 5 (3), 6 (3), 7 (4), 8 (2), 16 (1). Fable has *fewer* one-check misses than Astra or GPT-5.6-sol because it turns more of them into passes. Its remaining failures are a harder residue: 41 of the 44 are Hard70 tasks, and 29 are tasks none of the seven configurations solves.
  - On the 39 tasks both fail, Fable and Astra reach the same partial level (mean share 0.617 against 0.613).
  - On the 42 tasks both Fable and Opus 5 fail, Fable passes more checks (0.596 against 0.524; higher on 13 tasks, lower on 3).
- **Public reproduction.** 43 of the 44 failures pass it; the exception is 002, which has no verifier result.
- **Time limit.** Three runs hit the 90-minute limit (062, 107, 108). All three pass on workspace state.
- **Comparison with the paper's taxonomy.** The paper classifies Opus 5's 58 categorised failures as knowledge or abstraction (24), exploration or surface repair (2), repair coverage or system integration (21) and generalisation (11), plus 4 runtime or evaluation-path failures. We cannot assign Fable's failures to these classes without reading hidden checks. The count-level picture (passes the public check, passes most private checks, rarely fails all of them) fits "coverage" and "generalisation" better than "surface repair". This is an inference, not a classification.

## 5. Behaviour and cost (mechanical metrics only)

**Fable, all 119 tasks** (mean / median):

| Metric | Mean | Median |
|---|---|---|
| Input tokens (Pier `n_input_tokens`, incl. cache reads) | 5.30M | 4.59M |
| Output tokens | 166k | 153k |
| Of which thinking (116 runs) | 126k | 118k |
| Agent time | 38.3 min | 35.7 min |
| Turns (116 runs) | 72 | 63 |
| Peak context | 159k | 164k |
| Patch size | 99 kB | 14 kB |
| Files per patch | – | 2 |
| List cost per task (116 runs that report it) | $13.74 | $13.29 |

Cache reads are 94% of all input tokens. Total list cost is $1,594 for the 116 runs that report it (Claude Code's own estimate: $488, without a price basis for this model); the three time-limit runs end without Claude Code's final report and so report no cost, turns or thinking tokens. One run spawned a subagent, and none used TodoWrite.

**Tool mix** (`out/tool-mix.csv`, all 119 runs; medians; command text matched by regular expressions and never printed):

| Measure | Median |
|---|---|
| Tool calls | 61 |
| Bash calls | 44 |
| Read calls | 9 |
| Python or pytest executions | 22 |
| Mentions of the reproduction script | 7 |
| Scratch files written | 2 |
| First detected source edit | 17.6 min (about halfway through the session) |

The edit detection is heuristic; 8 runs have no detected source edit.

**Pass against fail within Fable** (medians):

| Measure | Pass (75) | Fail (44) |
|---|---|---|
| Input tokens | 4.59M | 4.67M |
| Output tokens | 153k | 153k |
| Agent time | 33.6 min | 36.9 min |
| Turns | 62.5 | 63 |
| Python executions | 23 | 20.5 |
| Thinking tokens | 106k | 130k |

Failing runs do not stop early or test less. They spend the same effort and more thinking, and still miss the hidden contract. Within Hard70 the pattern is the same.

**Leaderboard token figures** (mean per task, input / output):

| Configuration | Input | Output |
|---|---|---|
| Opus 5 (max) | 7.048M | 0.110M |
| GPT-6 Astra (max) | 1.404M | 0.021M |
| GPT-5.6-sol (max) | 3.921M | 0.027M |
| DeepSeek-V4-Pro (max) | 11.204M | 0.091M |
| Fable (xhigh) | 5.305M | 0.166M |

- Fable uses 25% less input than Opus 5, 1.5× its output, and 3.8× Astra's input.
- Over all 18 configurations, Spearman's rank correlation of Pass@1 is −0.32 with input tokens and −0.21 with output tokens.
- Caveat: the leaderboard does not say how it counts tokens. Pier's `n_input_tokens` for Claude Code includes cache reads. Opus 5's 7M is consistent with that counting, but we cannot verify it.

## 6. The paper's claims in light of the Fable result

| Claim (paper) | Verdict | Evidence |
|---|---|---|
| "Even the best-performing agent … achieves a pass@1 below 50%" (abstract; Opus 5 47.90%) | **Contradicted** (already by Astra at 50.42% on the leaderboard) | Fable 63.0%. The lower end of its Wilson 95% interval is 54.1%. |
| There is a large gap between public score and exact success (96.64% public against 47.90% Pass@1) | **Confirmed, still large** | Fable 99.2% public against 63.0% Pass@1. 43 of 44 failures pass the public reproduction. |
| "No single model leads every metric" (Table 2) | **Sharpened** | Fable leads Overall, Private and every per-task McNemar comparison. Public is at ceiling (100% without 002). Fail2Pass, Pass2Pass and the paradigm columns cannot be computed. |
| Performance differs by "how effectively each … configuration uses its context and generation budget, rather than … token volume alone" (Sec. 5.1) | **Consistent** | Fable is the top configuration with mid-range input tokens (5.3M, below Opus 5 and DeepSeek-V4-Pro). Rank correlation of Pass@1 with input tokens across 18 configurations is −0.32. Fable's output volume is among the highest. |
| Failure mechanisms are knowledge/abstraction, exploration/surface repair, coverage/integration and generalisation (Sec. 6.1) | **Not testable for Fable at our access level.** The counts fit under-implementation. | Failing patches pass the public reproduction and most private checks. Fable's failing runs show the same exploration and testing effort as its passing runs. |
| Scientific information helps weaker models more and stronger models less (Sec. 6.2, two models, descriptive) | **Not tested** | We did not run the ablation. Fable is equally strong on the 91-task ablation subset (63.7%) and the rest (60.7%), which says nothing about the effect of the information itself. |
| Few tasks per domain limit domain comparisons (Sec. 7) | **Confirmed** | 11 of the 20 domains have 1–3 tasks. Fable's per-domain lead is uniform rather than concentrated. |
| Hard70 (leaderboard): difficulty estimated from 12 earlier models | **Holds for a stronger model** | Fable 41.4% on Hard70 against 93.9% elsewhere. 41 of its 44 failures are Hard70 tasks. 29 of them are tasks none of the seven configurations solves. |
| Effort (the paper evaluates only at max) | **xhigh is no handicap for Fable** | Fable at xhigh beats every max configuration on the leaderboard. This run has no max-effort comparison of its own. |
| Paradigm pattern (Opus 5 leads Issue and Expert; Engineering is weakest for Opus 5) | **Cannot be evaluated for Fable** | Paradigm labels are unpublished. Fable's Engineering count is anywhere from 4 to 18 of 18. |

## 7. Two tasks at the level of approach

Two tasks that Fable passed and that none of the seven published configurations solves. We describe, at the level of approach only, what Fable did according to its own record. We did not read the hidden checks, so this is not a verified cause, and concrete fixes are not given here.

- **Ocean-grid sampling near the pole (parcels).** Before its first edit, Fable wrote a script that recorded search and interpolation results over a sweep of grid types and saved a baseline from the unmodified code. It then diffed old against new behaviour after every change. Its fix decides where spherical geometry applies by the shape of each grid cell, not by a latitude band around the pole.
- **Equivalent time zones giving different solar estimates (pvlib).** Before changing anything, Fable wrote a catalogue that evaluated every time-dependent public function under several equivalent representations of the same instants. It then fixed the defect wherever it appeared, not only in the function the public diagnostic calls.

In both, Fable treated the bug as an instance of a general rule rather than as the one case in the description.

---

## Claims to avoid

- "#1 on the SWE-bench Science leaderboard" or "state of the art": not an official or verified submission.
- Fable's Issue, Expert or Engineering Pass@1: the paradigm labels are unpublished and the split is not identifiable (Engineering anywhere from 22% to 100%).
- Fable's Fail2Pass and Pass2Pass: they cannot be computed from count-level data.
- "Fable solved tasks no model can solve": per-task data exists for 7 of the 17 configurations, and those tasks are hard, not unsolvable.
- Domain-level or language-level superiority ("better at physics"): cells hold 1–24 tasks. Supplied-materials and ablation-subset differences are descriptive only.
- Causal readings of the two approach descriptions ("Fable passed because it…"): the records show differences, not causes. Also do not describe what hidden checks test.
- "Xhigh is as good as max": this run has no matched max-effort comparison.
- Efficiency ratios against leaderboard token figures stated without the caveat that the leaderboard's token accounting is undocumented.

## Uncertainty summary

- **Task sampling.** Wilson 95% interval for Fable's Pass@1: 54.1–71.2%.
- **Run-to-run noise.** Not measured for Fable: one attempt per task. A rerun could move the total by a few tasks.
- **Comparability.** The leaderboard runs differ in effort (max), harness version, output cap and hardware, none of which is documented. The 3 runs that hit the 90-minute limit are scored on workspace state, as Pier does. Scoring them as failures gives 60.5% and leaves all conclusions unchanged.
- **002.** A verifier timeout is scored as a failure. Astra passed it.

## Files and reproduction

```bash
python -I analysis/fetch_inputs.py                 # leaderboard data at site commit f16153e, hash-checked
python -I analysis/summarise.py --check            # results/summary.json
python -I analysis/fable_vs_paper.py               # sections 1-5 and the extras; writes out/chart-leaderboard.csv
python -I analysis/tool_mix.py --summary           # tool-mix medians from out/tool-mix.csv
<python with scipy> -I analysis/paradigm_bounds.py # out/paradigm_bounds-output.txt
```

`fable_vs_paper.py` also writes `out/local/` (per-task tables that include other configurations' results; not committed).
