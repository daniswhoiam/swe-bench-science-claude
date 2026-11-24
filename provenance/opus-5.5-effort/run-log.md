# Run log: Claude Opus 5.5 at medium, high and max (earlier runs)

A dated account of the 344 earlier Opus 5.5 runs in `results/opus-5.5-effort/`, rewritten from the author's lab notes. All dates are UTC. Account details and the content of the other experiments are left out.

## What these runs are

From 11 to 16 November 2026, the author ran experiments on an Apple Silicon Mac that changed the agent's harness (extra review steps, plans, memory and similar). Every experiment had a baseline arm: Opus 5.5 with unmodified Claude Code, the same configuration as the scored runs in this repository except the effort level and the machine. This folder publishes those baseline runs and nothing else. The harness-variant arms ran on the same machine at the same time, but they are not part of this repository. On 24 November, 15 more baseline runs were made to cover the five tasks that had none.

| Arm | Effort | Runs |
|---|---|---|
| `A` | medium | 308, on all 119 tasks |
| `AH` | high | 18, on 18 tasks |
| `AX` | max | 18, on the same 18 tasks |

Fixed for every run:

- **Model and agent.** `anthropic/claude-opus-5-5`, Claude Code 2.1.293 as Pier 0.3.0's built-in agent, `reasoning_effort` as above.
- **Prompt and settings.** No prompt change and no `--agent-env`, so Claude Code's defaults apply: output cap 128,000 (reported in every usage report) and the native 1M context window, with no compaction in any run.
- **Limits.** The task's own 90-minute agent limit, one attempt per run.
- **Environment.** The same environment class and network policy as the scored runs (`harness/environment.py`; agent `isolated-allowlist` with only `api.anthropic.com`, verifier `none`; checked on every run).
- **Command.** The per-run Pier command is in `pier-command.txt`. The runs were started by the author's experiment driver, which also ran the unpublished arms and is not published. It issues one `pier run` per run, as `harness/run_fable.py` does.

## Machine

Apple Silicon Mac: 10 CPUs, 18.8 GB memory available to Docker, Docker Desktop 29.8.0, `DOCKER_DEFAULT_PLATFORM=linux/amd64`. The task images exist only for linux/amd64, so every container ran under emulation. Tool calls, builds and tests therefore ran slower than on the native x86 servers of the scored runs, by a factor that was not measured. Each container is allotted 2 CPUs by its `task.toml`, so with more than five runs at once the allotments exceeded the machine's 10 CPUs.

## Batches

| Dates | Runs (arm, seeds) | Tasks | Runs on the machine at once (median at a run's start, all experiments) |
|---|---|---|---|
| 11 Nov | 18 (`A`, seed 1) | 18 | 4 |
| 11 Nov | 73 (`A`, seed 1) | 73 further tasks of the default 96-task selection | 8 |
| 12 Nov | 143 (`A`, seeds 2 and 3) | the same 73 | 8 |
| 12 Nov | 36 (`AH` and `AX`, seed 1) | the 18 tasks of the first batch | 8 |
| 12 Nov | 13 (`A`, seed 4) | 13 of the 73 | 5 |
| 16 Nov | 46 (`A`, seeds 1 and 2) | the 23 restricted-licence tasks | 5 |
| 24 Nov | 15 (`A`, seeds 1 to 3) | 001, 002, 006, 014, 016 (no earlier baseline run) | 3 |

The order within each batch was a seeded random shuffle, different from the scored runs' `run-order.json`. The harness-variant arms ran interleaved with the baseline in the same batches, so machine load varied within and between batches.

Runs per task at medium: 1 on 19 tasks, 2 on 24, 3 on 63 and 4 on 13 (`results/opus-5.5-effort/per-task.csv`).

## Sessions not in the data

Every recorded run is published, including the four that hit the time limit. The only exclusions are 10 sessions that never produced a recorded outcome. None was dropped because of its result.

- **12 Nov, 2 sessions** (seed 2 of tasks 047 and 109). They were running when the batch was stopped early, because the harness comparison it served had become futile under its pre-registered rule. The sessions were discarded, and seed 3 of task 047 never started. These two tasks therefore have fewer medium runs.
- **12 Nov, 3 sessions** (seed 4 of tasks 004, 095 and 104). They were running when the seed-4 baseline was discontinued to speed up the concurrent harness arm. That decision was taken for speed, before any analysis. The sessions were discarded and not rerun, so seed 4 exists for 13 tasks only.
- **12 Nov, 1 session.** Its image pull failed before the agent started (an infrastructure failure under the driver's rule). It was rerun.
- **13 Nov, 4 job folders** (seeds 1 and 2 of tasks 083 and 085). The driver could not record them, because its record builder looked for these restricted-licence tasks in a task folder that did not contain them, and the remaining sessions were interrupted when all local runs were paused. They were set aside without a recorded outcome. Both tasks were rerun from scratch on 16 Nov, after the fix.

The driver's rule for infrastructure failures: a session whose agent never started, or that died within 90 seconds, is rerun. No other rerun happened.

## Task folders

The first five batches (283 runs, 11-12 Nov) used an older materialisation of the 96-task default selection. The last two batches (61 runs) used `tasks-selected-all`, the folder of the scored runs. The two folders are byte-identical except for one extra file, `batch-run.json`, at the top level of each task in the older copy. The benchmark's `scripts/run_batch.py` wrote it during a smoke test; it records the smoke command and the image references, not task content. Pier copies neither the task's top level into the agent's container nor anything but `tests/` into the verifier's. The extra file changes Pier's task digest, which is why those 283 runs have a different `task_digest` and `task_checksum` from the scored runs. Recomputed with Pier's own hash function, every digest matches the folder named here. The image references, limits and environment settings are the same as in the scored runs for all 344 runs (`per-run-provenance.jsonl`).

## Records

- The run records were built with the same record builder as the scored runs (`harness/record.py` is that builder, trimmed of fields that belonged to other experiments). The published fields are the same as for the scored runs (`results/README.md`).
- `token_prefix_hits` is 0 for all 344 runs.
- 24 Nov: count-only network scan of all 344 agent records (`docs/network-scan-opus-5.5-effort.md`).
