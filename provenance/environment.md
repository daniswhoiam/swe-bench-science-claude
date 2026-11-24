# Environment

Two scored passes, identical except for the rows marked *per run*: Claude Fable 5.2 at xhigh (servers A and B, 13-17 Nov 2026) and Claude Opus 5.5 at max (server C, 23-24 Nov 2026).

## Software

| Item | Value |
|---|---|
| Runner | `datacurve-pier==0.3.0` (the benchmark's harness), `pier run`, one job per task (`provenance/pier-command.txt`, `provenance/opus-5.5-max/pier-command.txt`) |
| Agent | Pier's built-in `claude-code` agent, Claude Code **2.1.293** installed in each agent container (`--agent-kwarg version=2.1.293`) |
| Model *(per run)* | Fable 5.2: `anthropic/claude-fable-5-2`; Claude Code reported `claude-fable-5-2` in all 119 runs and no other model in its 116 usage reports. Opus 5.5: `anthropic/claude-opus-5-5`; reported as `claude-opus-5-5` in all 119 runs and no other model in its 115 usage reports |
| Effort *(per run)* | Fable 5.2: `--agent-kwarg reasoning_effort=xhigh`. Opus 5.5: `--agent-kwarg reasoning_effort=max` |
| Agent environment *(per run)* | Fable 5.2: `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000` (`--agent-env`; Pier masks the value as `****` in its job files). Opus 5.5: none; Claude Code's own defaults (it reports `maxOutputTokens: 128000` for `claude-opus-5-5`) |
| Credential | `--env-file <env-file>`: a file outside the project holding `CLAUDE_CODE_OAUTH_TOKEN` (a Claude subscription token). The same file for both passes. Its values never appear in Pier's files |
| Environment class | `harness.environment:MirroredScienceBenchDocker`: the benchmark's `ScienceBenchDocker` (`scripts/pier_network.py`), changed only in how the egress-proxy image is built (an Ubuntu mirror for its `apt-get`) |
| Network | agent `isolated-allowlist` with inference domain `api.anthropic.com` (squid egress proxy, policy `internal-isolated-squid-v1`, no proxy forwarding, no host gateway); verifier `none`. Recorded per trial in `per-task-provenance.jsonl` |
| Python | 3.12 virtual environment, same package list on all three servers |
| Driver | `harness/run_fable.py` (`--config fable-xhigh`: concurrency 7 on server A, 6 on server B; `--config opus-max`: 6 on server C) |

## Dataset

| Item | Value |
|---|---|
| Source | Hugging Face `OpenMOSS-Team/SWE-bench-Science`, revision `997408298e8e4d09978b1120b95c4540d1a71bcb` |
| Manifest | `manifests/tasks.jsonl`, sha256 `bcada90a99fcfd88e67ff4faf38af8ad3dad354b32a5a904a75d378e29ca8d4c` |
| Tasks | all 119, materialised with `scripts/materialize.py --allow-restricted-licenses --output tasks-selected-all` |
| Limits (each `task.toml`, unchanged) | agent 5400 s, verifier 1800 s, 2 CPUs, 8192 MB memory, 20480 MB storage, `allow_internet = false` |
| Images | per task, environment and verifier image references with digests in `per-task-provenance.jsonl` (`task_toml`), plus Pier's task digest and checksum |

## Hardware

All three servers were rented bare-metal machines, native linux/amd64 (the task images exist only for linux/amd64), each used only for these runs and wiped afterwards.

| | Server A (Fable 5.2) | Server B (Fable 5.2) | Server C (Opus 5.5) |
|---|---|---|---|
| CPU | Intel Core i9-13900 (32 threads) | Intel Core i5-12500 (6 cores, 12 threads) | Intel Core i5-12500 (6 cores, 12 threads) |
| Memory | 64 GB | 64 GB | 64 GB |
| OS | Ubuntu 24.04.5 | Ubuntu 24.04.5 | Ubuntu 24.04.5 |
| Docker | 29.9.3 | 29.10.0 | 29.10.0 |
| Concurrent tasks | 7 | 6 | 6 |
| Tasks | 92 (run-order positions 1-91 and 93) | 27 (positions 92 and 94-119) | all 119 |
| Dates (UTC) | 13 Nov 2026 11:48 to 14 Nov 05:19 | 17 Nov 2026 11:08 to 14:53 | 23 Nov 2026 11:14 to 24 Nov 00:15 |
| Passed | 56/92 | 19/27 | 71/119 |

Before each pass, the same smoke task was run on each server at medium effort to check the setup; those smoke runs are not part of either result.

`per-task.csv` (`server`) and `per-task-provenance.jsonl` give the server per task. The run order is random and the same for both passes (`run-order.json`, seed 20261111), so the split between servers A and B is not tied to task difficulty.
