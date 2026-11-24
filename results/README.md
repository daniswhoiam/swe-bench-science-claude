# results/

Per-task results of the scored runs (one attempt per task). Generated from the run records by a whitelist of fields; nothing here is copied from a job folder.

- This folder: Claude Fable 5.2, xhigh (119 runs).
- [`opus-5.5-max/`](opus-5.5-max/): Claude Opus 5.5, max (119 runs). The same four files with the same columns and fields.

Values that differ between the two runs are listed under [Run-specific values](#run-specific-values).

| File | Content |
|---|---|
| `per-task.csv` | one row per task (dictionary below) |
| `runs.jsonl` | the same 119 runs as structured records (field subset of `harness/record.py`'s output) |
| `summary.json` | headline aggregates, written by `analysis/summarise.py` from the two files above |
| `artefact-checksums.csv` | SHA-256 and size of each run's `model.patch` (the patches themselves are not published) |

## `per-task.csv`

Sources: R = run record (`runs.jsonl`), T = the dataset's `data/tasks.csv` (MIT, OpenMOSS), P = paper Table 5 (CC BY 4.0), O = `provenance/run-order.json`, H = the leaderboard's Hard70 list. Empty cell = no value.

| Column | Source | Meaning |
|---|---|---|
| `task_id` | | three-digit task ID (`001`-`119`) |
| `title`, `domain`, `language` | T | task metadata as published by the benchmark |
| `paper_domain` | P | one of the paper's 20 scientific domains |
| `license_gate` | T | `none`, `gpl-family`, `noncommercial` or `restricted-materials` |
| `restricted_license` | T | True for the 23 tasks that need `--allow-restricted-licenses` |
| `in_default_96` | T | in the default 96-task selection (`selections/default-96.json`) |
| `has_materials` | T | `material_license` is set: the task ships third-party scientific material |
| `science_knowledge_ablation` | T | in the paper's 91-task science-knowledge ablation subset |
| `hard70` | H | in the leaderboard's Hard70 subset |
| `run_order` | O | position in the seeded random run order (1-119), the same for both runs |
| `server` | R `started_at` | `A` (i9-13900) or `B` (i5-12500) for Fable 5.2, `C` (i5-12500) for Opus 5.5; see `provenance/environment.md` |
| `status` | R | `completed`; `agent_time_limit` (hit the 90-minute limit, scored on the workspace); `verifier_timeout` (no verifier result, scored as a failure) |
| `pass_at_1` | R `verifier.reward` | 1 if every private test passes and the public reproduction passes; 0 otherwise. Equals "all private tests pass" on all 119 tasks in both runs |
| `public_reproduction_pass` | R | 1 if the public reproduction script exited with code 0 |
| `public_passed`, `public_total` | R | public tests passed / collected by the verifier. Empty when the verifier produced no result |
| `private_passed`, `private_total` | R | private (hidden) tests passed / collected. Empty when the verifier produced no result |
| `agent_min`, `verifier_min`, `wall_min` | R `wall_sec` | agent execution, verifier, and whole trial, in minutes |
| `num_turns` | R | Claude Code's turn count (empty for time-limit runs, which end without a final report) |
| `n_tool_calls`, `n_bash_calls` | R | tool calls and Bash calls in the trajectory |
| `n_edit_tool_calls` | R | Edit, Write, MultiEdit and NotebookEdit calls |
| `n_bash_edit_like` | R | Bash calls that look like in-place edits (a regular-expression heuristic: `sed -i`, heredocs, `.write(` and similar) |
| `input_tokens` | R `usage.pier.n_input_tokens` | input tokens **including cache reads** (Pier's count) |
| `cache_read_tokens` | R `usage.pier.n_cache_tokens` | the cache-read part of `input_tokens` |
| `output_tokens` | R `usage.pier.n_output_tokens` | output tokens, including thinking |
| `thinking_tokens` | R | thinking tokens as reported by Claude Code (empty for time-limit runs) |
| `peak_context_tokens` | R | largest context Pier observed |
| `list_cost_usd` | R | Claude Code's own cost estimate (its final session total) at API list prices; not what was paid (a subscription was used). Empty for time-limit runs |
| `subagents_spawned` | R | subagents started by Claude Code |
| `patch_bytes`, `patch_files_count`, `patch_sha256` | R | size, number of files touched, and SHA-256 of the final `model.patch`. The list of files is not published |
| `agent_network`, `verifier_network` | R | network mode recorded by the benchmark's policy for the agent and verifier containers |
| `model_reported`, `claude_code_version_reported` | R | as reported by Claude Code's session start |
| `started_at_utc`, `finished_at_utc` | R | trial start and end |

## `runs.jsonl`

One JSON object per run with: `run_id`, `task`, `status`, `exception_type`, `model_id` (requested, reported), `effort`, `claude_code_version` (requested, reported), `agent_timeout_sec`, `started_at`, `finished_at`, `wall_sec` (per stage), `usage.pier` (Pier's token and cost counters), `usage.claude_code` (Claude Code's final report: turns, durations, tokens, `model_usage` per model, subagents), `edits` (counts only), `patch` (`bytes`, `sha256`), `verifier` (`reward`, `public` and `private` counts and return codes, `hidden_pass`, `public_pass`), `network`, `pier_exit_code`, `token_prefix_hits`.

- `run_id` is the Pier job name `<arm>-<task>-s1`: arm `FXH` (Fable 5.2, xhigh) or `OX` (Opus 5.5, max), seed 1. The private artefacts are filed under the same names.
- `token_prefix_hits` is the number of files in the job folder and Pier log that contain the OAuth token prefix; 0 for all 119 runs of both models.

Left out on purpose: the job folder path and trial name, the list of files each patch touches, the unpatched-base verifier counts and anything derived from them (Fail2Pass/Pass2Pass estimates), and fields of other experiments that are empty for these runs.

## `artefact-checksums.csv`

`task_id`, `run_id`, `artefact` (`model.patch`), `bytes`, `sha256`, from the record builder, which hashed each patch when the run was recorded. They are a commitment: the patches are available to the benchmark maintainers, who can check them against this file. Transcripts are not hashed here.

## Run-specific values

**Claude Fable 5.2, xhigh** (this folder):

- `server` is `A` for 92 tasks and `B` for 27 (run-order positions 92 and 94-119).
- `status`: 3 runs hit the 90-minute limit (062, 107, 108; all pass), and 1 is a verifier timeout (002, no public or private counts).
- `usage.claude_code.model_usage.claude-fable-5-2.maxOutputTokens` reads 32000 in every run that has the field, although `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000` was passed to every session (`provenance/pier-command.txt`). The field is reported by Claude Code as is, but it does not reflect the effective cap: in the 41 runs whose session files were inspected, 18 single responses exceeded 32,000 output tokens (the largest 91,727), which the default cap would have ended with an API error. The raised cap was therefore in effect and was used.
- `list_cost_usd` equals Pier's `usage.pier.cost_usd` in every run that has a cost.

**Claude Opus 5.5, max** ([`opus-5.5-max/`](opus-5.5-max/)):

- `server` is `C` for every task (i5-12500; see `provenance/environment.md`).
- `status`: 4 runs hit the 90-minute limit (001, 014, 033, 040; 001 passes). No run is a verifier timeout; every run has public and private counts.
- `usage.claude_code.model_usage.claude-opus-5-5.maxOutputTokens` reads 128000 in every run that has the field, and no `--agent-env` was passed. In the session files, 56 single responses exceeded 32,000 output tokens (the largest 100,586) in 45 runs, without an API error, so the default cap for Opus 5.5 in Claude Code 2.1.293 is above 32,000.
- `list_cost_usd`: for 037 and 081, where background subagents made the session emit several result events, Pier's `usage.pier.cost_usd` and token counts are lower than Claude Code's final session total; all other runs agree to the cent.
