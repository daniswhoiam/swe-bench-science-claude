# Environment

## Software

| Item | Value |
|---|---|
| Runner | `datacurve-pier==0.3.0` (the benchmark's harness), `pier run`, one job per task (`provenance/pier-command.txt`) |
| Agent | Pier's built-in `claude-code` agent, Claude Code **2.1.293** installed in each agent container (`--agent-kwarg version=2.1.293`) |
| Model | `anthropic/claude-fable-5-2`; Claude Code reported `claude-fable-5-2` in all 119 runs and no other model in its usage reports |
| Effort | `--agent-kwarg reasoning_effort=xhigh` |
| Agent environment | `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000` (`--agent-env`; Pier masks the value as `****` in its job files) |
| Credential | `--env-file <env-file>`: a file outside the project holding `ANTHROPIC_AUTH_TOKEN` (a Claude subscription token). Its values never appear in Pier's files |
| Environment class | `harness.environment:MirroredScienceBenchDocker`: the benchmark's `ScienceBenchDocker` (`scripts/pier_network.py`), changed only in how the egress-proxy image is built (an Ubuntu mirror for its `apt-get`) |
| Network | agent `isolated-allowlist` with inference domain `api.anthropic.com` (squid egress proxy, policy `internal-isolated-squid-v1`, no proxy forwarding, no host gateway); verifier `none`. Recorded per trial in `per-task-provenance.jsonl` |
| Python | 3.12 virtual environment, same package list on both servers |
| Driver | `harness/run_fable.py` (concurrency 7 on server A, 6 on server B) |

## Dataset

| Item | Value |
|---|---|
| Source | Hugging Face `OpenMOSS-Team/SWE-bench-Science`, revision `997408298e8e4d09978b1120b95c4540d1a71bcb` |
| Manifest | `manifests/tasks.jsonl`, sha256 `bcada90a99fcfd88e67ff4faf38af8ad3dad354b32a5a904a75d378e29ca8d4c` |
| Tasks | all 119, materialised with `scripts/materialize.py --allow-restricted-licenses --output tasks-selected-all` |
| Limits (each `task.toml`, unchanged) | agent 5400 s, verifier 1800 s, 2 CPUs, 8192 MB memory, 20480 MB storage, `allow_internet = false` |
| Images | per task, environment and verifier image references with digests in `per-task-provenance.jsonl` (`task_toml`), plus Pier's task digest and checksum |

## Hardware

Both servers were rented bare-metal machines, native linux/amd64 (the task images exist only for linux/amd64), used only for this run.

| | Server A | Server B |
|---|---|---|
| CPU | Intel Core i9-13900 (32 threads) | Intel Core i5-12500 (6 cores, 12 threads) |
| Memory | 64 GB | 64 GB |
| OS | Ubuntu 24.04.5 | Ubuntu 24.04.5 |
| Docker | 29.9.3 | 29.10.0 |
| Concurrent tasks | 7 | 6 |
| Tasks | 92 (run-order positions 1-91 and 93) | 27 (positions 92 and 94-119) |
| Dates (UTC) | 13 Nov 2026 11:48 to 14 Nov 05:19 | 17 Nov 2026 11:08 to 14:53 |
| Passed | 56/92 | 19/27 |

Before each pass, the same smoke task was run on each server with a different model to check the setup; those smoke runs are not part of the result.

`per-task.csv` (`server`) and `per-task-provenance.jsonl` give the server per task. The run order is random (`run-order.json`, seed 20261111), so the split between the servers is not tied to task difficulty.
