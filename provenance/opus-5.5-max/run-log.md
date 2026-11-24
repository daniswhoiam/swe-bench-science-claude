# Run log: Claude Opus 5.5, max effort

A dated timeline of the Opus 5.5 pass, rewritten from the author's lab notes. All times are UTC (the server ran on UTC+1). Machine names, account details and notes about other experiments are left out.

## Before the pass (23 Nov 2026)

- **Purpose.** A baseline under the paper's headline condition (Claude Code at max effort, everything else at its defaults) for submission to the benchmark maintainers.
- **Configuration frozen** (before launch): all 119 tasks, `anthropic/claude-opus-5-5`, Claude Code 2.1.293 as Pier 0.3.0's built-in agent, `reasoning_effort=max`, no prompt changes, no `--agent-env`, the task's own 90-minute limit, one attempt per task, the benchmark's network policy with the same one change to the proxy image build as the Fable pass (`harness/environment.py`). Same set-aside rule as the Fable pass: sessions that end on a usage limit or another API error are set aside and rerun from scratch; runs that hit the time limit are scored on their workspace, as Pier does.
- **Output cap.** No override. In earlier Opus 5.5 max-effort test runs on another machine (not part of the pass), Claude Code reported `maxOutputTokens: 128000` for `claude-opus-5-5` and no session ended on an output-cap error. The pass confirmed it: in the session files, 56 single responses exceeded 32,000 output tokens (largest 100,586) in 45 runs, and none ended in an error.
- **Run order:** the same seeded shuffle as the Fable pass (seed 20261111), `run-order.json` in this folder (task order identical to `provenance/run-order.json`).
- **Server C** set up from scratch (`provenance/environment.md`). Smoke task 053 at medium effort passed; not part of the result.

## The pass (23-24 Nov)

- **23 Nov 11:14.** Pass started (arm `OX`), 6 tasks at a time.
- **23 Nov 21:00.** The subscription's usage meter stood at 96%, with a reset at 22:00. To avoid cutting running sessions at the limit, new task starts were paused (a `STOP` file) with 95 of 119 recorded and 6 running; the running tasks continued. A script on the server restarted the same driver command once the running tasks had finished and the reset had passed. The decision was made on the usage meter, not on any result.
- **23 Nov 22:26.** The six running tasks had finished; the driver exited and was restarted at once by the script. Recorded runs were skipped; the remaining 18 tasks continued in the same order.
- **24 Nov 00:14.** Last task finished. **Final: 71/119 Pass@1.**
- The usage limit was never reached: 0 limit waits, 0 set-aside sessions, 0 driver errors, 0 verifier timeouts. Four runs hit the 90-minute agent limit (001, 014, 033, 040) and are scored on their workspace; 001 passes.

## After the pass

- All job folders were copied from the server and checked against it with a checksum dry run (0 files differing) before the server was wiped. The credential file was shredded, the run folders deleted, and a search of the whole filesystem found no file containing the token prefix.
- Records: `harness/record.py` built `runs.jsonl`; `token_prefix_hits` is 0 for all 119 runs (job folders and Pier logs).
- 24 Nov: count-only network scan of the 119 agent records with the unchanged patterns of the Fable scan (`docs/network-scan-opus-5.5-max.md`).
