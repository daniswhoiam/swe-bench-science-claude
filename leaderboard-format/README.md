# leaderboard-format/

This run's per-task results in the schemas of the SWE-bench Science leaderboard site (`swescience/swescience.github.io`, `data/`), so that the maintainers can merge them if they decide to list the result. It is **not** an official entry and has not been audited by the maintainers.

| File | Schema on the site | Content |
|---|---|---|
| `task-matrix-entry.json` | `data/task-matrix.json` | `{version, generatedAt, models: [our model], tasks: [119 x {publishedTaskId, scientificKnowledgeAblation, results: {fable-5-2-xhigh: {public, private, reward, transition, source}}}]}` |
| `benchmark-entry.json` | one element of `models` in `data/benchmark.json` | `id`, `family`, `reasoningDepth`, `harness`, `scores`, `tokens` |
| `hard70-entry.json` | `data/hard70-model-results.json` | `{version, taskCount: 119, modelPasses: {fable-5-2-xhigh: [75 task IDs]}}` |
| `validate_entry.py` | | re-implements the site's checks for a per-task entry and, after `analysis/fetch_inputs.py`, merges the entry into the site's matrix in memory |

`legacyTaskId` is left out of the task entries; it is the same mapping for every model and can be taken from the site's file when merging. `generatedAt` is a placeholder until publication.

## Scores

| Field | Value | How |
|---|---|---|
| `overall` | 63.03 | Pass@1: 75/119 tasks with reward 1 |
| `public` | 99.16 | macro mean over 119 tasks of public tests passed / total |
| `private` | 85.26 | macro mean over 119 tasks of private tests passed / total |
| `fail2Pass`, `pass2Pass` | `null` | need per-test results before and after the patch; this run's records hold pass counts only |
| `issue`, `expert`, `engineering` | `null` | the task-to-paradigm labels are not published (`analysis/paradigm_bounds.py` shows the split is not identifiable) |
| `tokens.input` | 5.305 | mean Pier `n_input_tokens` per task, in millions; **includes cache reads** (94% of all input tokens). Uncached input alone: 0.330M per task |
| `tokens.output` | 0.166 | mean Pier `n_output_tokens` per task, in millions (includes thinking) |

The site's validator rejects `null` scores, so the entry cannot go in as a pull request. Only the maintainers can complete it, for example by re-evaluating the patches. We do not know how the leaderboard counts tokens; the split above lets them convert.

## Conventions

- **002** (verifier timeout; the verifier ran for an hour without a result) is recorded as public 0/1 and private 0/8: zero passed out of the leaderboard's totals for that task. This is the convention the leaderboard uses for an evaluation that produced nothing (Kimi-K3 on 061: 0/1). It gives the 99.16 / 85.26 macro values. Without 002: 100.00 / 85.98 over 118 tasks.
- **032**: our verifier image collects 6 private tests, the leaderboard lists 21. The task passes either way. The entry records what our verifier collected (6/6); it is flagged here, not corrected.
- **062, 107, 108** hit the 90-minute agent limit and are scored on their workspace state, as Pier does. All three pass. Scored as failures instead, Pass@1 would be 72/119 = 60.50%.
- **`source`** on every task: "External run by Daniil Belazovschi: Pier 0.3.0, Claude Code 2.1.293, xhigh; not audited by the maintainers".
- **Hard70**: the site's validator needs the full pass list to recompute overall Pass@1, so `hard70-entry.json` lists all 75 passed tasks, not only the 29 Hard70 ones.

Run `python -I leaderboard-format/validate_entry.py` to check all of the above.
