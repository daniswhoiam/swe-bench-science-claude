# leaderboard-format/

The per-task results of both runs in the schemas of the SWE-bench Science leaderboard site (`swescience/swescience.github.io`, `data/`), so that the maintainers can merge them if they decide to list them. Neither is an official entry, and neither has been audited by the maintainers.

- Claude Fable 5.2, xhigh (model id `fable-5-2-xhigh`, family `Claude-Fable-5.2`, `reasoningDepth` `xhigh`): the files in this folder.
- Claude Opus 5.5, max (model id `opus-5-5-max`, family `Claude-Opus-5.5`, `reasoningDepth` `max`): the same three files in [`opus-5.5-max/`](opus-5.5-max/).

| File | Schema on the site | Content |
|---|---|---|
| `task-matrix-entry.json` | `data/task-matrix.json` | `{version, generatedAt, models: [the model], tasks: [119 x {publishedTaskId, scientificKnowledgeAblation, results: {<model id>: {public, private, reward, transition, source}}}]}` |
| `benchmark-entry.json` | one element of `models` in `data/benchmark.json` | `id`, `family`, `reasoningDepth`, `harness`, `scores`, `tokens` |
| `hard70-entry.json` | `data/hard70-model-results.json` | `{version, taskCount: 119, modelPasses: {<model id>: [the passed task IDs]}}` |
| `validate_entry.py` | | re-implements the site's checks for a per-task entry and, after `analysis/fetch_inputs.py`, merges the entry into the site's matrix in memory (`--run opus` for the Opus 5.5 files) |

`legacyTaskId` is left out of the task entries; it is the same mapping for every model and can be taken from the site's file when merging. `generatedAt` is the release date of each entry.

## Scores

| Field | Fable 5.2 | Opus 5.5 | How |
|---|---|---|---|
| `overall` | 63.03 | 59.66 | Pass@1: tasks with reward 1 (75 and 71 of 119) |
| `public` | 99.16 | 100.00 | macro mean over 119 tasks of public tests passed / total |
| `private` | 85.26 | 85.78 | macro mean over 119 tasks of private tests passed / total |
| `fail2Pass`, `pass2Pass` | `null` | `null` | need per-test results before and after the patch; the records of both runs hold pass counts only |
| `issue`, `expert`, `engineering` | `null` | `null` | the task-to-paradigm labels are not published (`analysis/paradigm_bounds.py` shows, for the Fable 5.2 result, that the split is not identifiable) |
| `tokens.input` | 5.305 | 12.518 | mean Pier `n_input_tokens` per task, in millions; **includes cache reads** (94% and 98% of all input tokens). Uncached input alone: 0.330M and 0.277M per task |
| `tokens.output` | 0.166 | 0.167 | mean Pier `n_output_tokens` per task, in millions (includes thinking) |

The site's validator rejects `null` scores, so neither entry can go in as a pull request. Only the maintainers can complete them, for example by re-evaluating the patches. It is not known how the leaderboard counts tokens; the split above lets the maintainers convert.

## Conventions

Both entries:

- **032**: the verifier image collects 6 private tests, the leaderboard lists 21. The task passes either way. The entries record what the verifier collected (6/6); it is flagged here, not corrected.
- **Time-limit runs** are scored on their workspace state, as Pier does.
- **An evaluation that produced nothing** is recorded as zero passed out of the leaderboard's totals for that task, the convention the leaderboard uses (Kimi-K3 on 061: 0/1).
- **Tokens** come from Pier's counters for every task.
- **`source`** on every task: "External run by Daniil Belazovschi: Pier 0.3.0, Claude Code 2.1.293, `<effort>`; not audited by the maintainers", with `xhigh` or `max`.
- **Hard70**: the site's validator needs the full pass list to recompute overall Pass@1, so each `hard70-entry.json` lists all passed tasks, not only the Hard70 ones.

Fable 5.2:

- **002** (verifier timeout; the verifier ran for an hour without a result) is recorded as public 0/1 and private 0/8. This gives the 99.16 / 85.26 macro values. Without 002: 100.00 / 85.98 over 118 tasks.
- **062, 107, 108** hit the 90-minute agent limit; all three pass. Scored as failures instead, Pass@1 would be 72/119 = 60.50%.
- `hard70-entry.json` lists all 75 passed tasks (29 of them in Hard70).

Opus 5.5:

- Every task has a verifier result; no verifier timeout.
- **001, 014, 033, 040** hit the 90-minute agent limit; 001 passes. Scored as failures instead, Pass@1 would be 70/119 = 58.82%.
- **037 and 081**: background subagents made the session emit several result events, so Pier's token counts (used here, as for every task) and its cost are lower than Claude Code's final session totals. The list cost in `results/opus-5.5-max/per-task.csv` is computed from Claude Code's totals.
- `hard70-entry.json` lists all 71 passed tasks (24 of them in Hard70).

Run `python -I leaderboard-format/validate_entry.py` (Fable 5.2) and `python -I leaderboard-format/validate_entry.py --run opus` (Opus 5.5) to check all of the above.
