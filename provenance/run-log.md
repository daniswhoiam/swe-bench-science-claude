# Run log: Claude Fable 5.2, xhigh effort

A dated timeline of the Fable 5.2 pass, rewritten from the author's lab notes. All times are UTC (the servers ran on UTC+1). Machine names, account details and notes about other experiments are left out.

## Before the pass (12-13 Nov 2026)

- **Configuration frozen** (12 Nov, before any scored run): all 119 tasks, `anthropic/claude-fable-5-2`, Claude Code 2.1.293 as Pier 0.3.0's built-in agent, no prompt changes, the task's own 90-minute limit, one attempt per task, the benchmark's network policy with one change to the proxy image build (`harness/environment.py`). Sessions that end on a usage limit or another API error are set aside and rerun from scratch; runs that hit the time limit are scored on their workspace, as Pier does.
- **Output cap.** In test runs on another machine (not part of the pass), a max-effort session ended with an API error when one response exceeded Claude Code's default 32,000 output tokens. With `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000` the same task completed normally. The raised cap became part of the frozen configuration.
- **Run order** fixed: a seeded shuffle of the 119 tasks (seed 20261111), `run-order.json`.

## Server A (13-14 Nov)

- **13 Nov 10:05.** Pass started at **max** effort, 7 tasks at a time.
- **13 Nov 10:52.** After 47 minutes none of the first seven tasks had finished. The pass was switched to **xhigh** for cost and time. No max-effort outcome existed at that point. The seven max-effort sessions were left to finish; they are not part of the result and not in this repository. The 112 queued tasks never started at max.
- **13 Nov 11:48.** xhigh pass started (arm `FXH`), same frozen configuration, all 119 tasks in the same order. Two faults were found and fixed before any xhigh task finished: the script that was to start the xhigh pass automatically never fired, so the pass was started by hand 13 minutes after the max-effort driver exited; the record builder read `task.toml` from a fixed folder that lacked the 23 restricted-licence tasks (fixed on the server by pointing that folder at the full task set; the public `harness/record.py` takes the folder as a parameter).
- **13 Nov 17:30.** The subscription's usage limit was reached. The driver's limit pattern did not recognise the message wording, so the affected sessions were treated as other session errors: set aside, rerun from scratch twice, and the driver halted at 17:51 as designed. No recorded run was affected. The pattern was extended to any session error that mentions a limit (the version in `harness/run_fable.py`).
- **14 Nov 02:02.** Driver restarted after the limit reset; recorded runs were skipped, the remaining tasks continued in the same order.
- **14 Nov 05:24.** Usage limit reached again. The driver now recognised it and waited in 30-minute steps, setting aside each cut-off session.
- **14 Nov 09:30.** Pass stopped by the author with 92 of 119 tasks recorded (run-order positions 1-91 and 93; 56 passed). Five runs in progress at that moment were cut off when the server was shut down (tasks 072, 079, 088, 106, 117). They were never scored; all five were rerun from scratch on server B.
- Set-aside sessions over the whole pass: 79 session folders on 13 tasks, all from the two usage-limit stops. The set-aside rule reads only the session's own error text, never the verifier result.

## Server B (17 Nov)

- A second rented server (`environment.md`), same software versions and frozen configuration, concurrency 6 (12 threads at 2 CPUs per container).
- The 92 recorded runs were copied back and skipped; the driver regenerated the order from the same seed, identical to `run-order.json`.
- **17 Nov 11:08-14:53.** The remaining 27 tasks ran with no usage-limit stop, no set-aside session and no driver error. 19 of 27 passed.
- **Final:** 75/119 Pass@1.

## After the pass

- All job folders were copied from both servers and checked against the servers with a checksum dry run (0 files differing) before the servers were wiped. The credential files were shredded and the run folders deleted.
- Records: `harness/record.py` built `runs.jsonl`; `token_prefix_hits` is 0 for all 119 runs (job folders and Pier logs).
- 17 Nov: count-only network scan of the 119 agent records (`docs/network-scan.md`).
