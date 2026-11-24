# Network and download attempts in the agent records: earlier Claude Opus 5.5 runs (medium, high, max)

A count-only scan of the agent records of all 344 earlier Opus 5.5 runs in `results/opus-5.5-effort/` (308 at medium, 18 at high, 18 at max). It was made on 2026-11-24 with the same fixed patterns as the scans of the two scored runs; method, pattern list and limits are in [`network-scan.md`](network-scan.md). Script: [`analysis/contamination_scan.py`](../analysis/contamination_scan.py). Per-run counts: [`analysis/out/opus-5.5-effort/contamination-scan.csv`](../analysis/out/opus-5.5-effort/contamination-scan.csv), with run IDs, task IDs, counts and reason codes only.

## Summary

The agent never used its web-fetch or web-search tools, though both were available in every run. No tool result in any of the 344 runs contains a success string.

- **`pip download`.** 55 calls in 53 runs. 54 results show a blocked-network error, and 1 shows neither a blocked nor a success signal.
- **Other shell network commands.** 1 curl/wget call, blocked. 3 non-local `pip install`/`uv` calls in 2 runs: one blocked, and 2 in task 018 with no signal (018 showed the same in the Fable 5.2 scan).
- **Never seen.** git, ssh and system package managers.
- **Inline code.** 7 Bash calls with network code or a URL in 5 runs. In the 3 runs that could be read, these are URLs in a docstring written into a source file, not network requests.

The flagged runs are listed below by run ID and counts, as in the other scans, so that the maintainers can inspect them. 44 of them were scanned without being read.

## What was scanned

- **Scope.** All 344 runs in `results/opus-5.5-effort/per-run.csv`. Sessions that never produced a recorded outcome (`provenance/opus-5.5-effort/run-log.md`) are not part of the data and were not scanned.
- **Record.** Per run, only the agent's own session record (`agent/claude-code.txt`, Claude Code's stream-JSON). All 344 runs had it. Nothing under `verifier/` or a task's `tests/` was opened.
- **Patterns, units and flags.** Identical to the other scans. The script now also accepts several job folders and the job names of these runs (`A-`, `AH-`, `AX-<task>-s<seed>`). With `--run-ids` it adds the job name as a first column. Run on the job folders of the two scored runs, it still reproduces `analysis/out/contamination-scan.csv` and `analysis/out/opus-5.5-max/contamination-scan.csv` exactly. The 151 self-checks passed before the scan.
- **Reading.** For most runs, only counts and run IDs left the script. For the rest, the matched lines were read to describe what happened (summarised below without run IDs).

## Totals over the 344 runs

Each cell is calls (or results) / runs with at least one.

| Category | All 344 runs |
|---|---|
| A. WebFetch / WebSearch tool calls, server web blocks, usage web counters | **0 / 0** |
| B. Shell network commands (excluding pip-local) | 59 / 56 |
| of which `pip download` | 55 / 53 |
| of which curl or wget | 1 / 1 |
| of which non-local `pip install` / `uv` | 3 / 2 |
| `git clone/fetch/pull`, conda/npm/apt/cargo/go, svn/hg, ssh/scp/nc/telnet | 0 / 0 |
| B-pip-local | 1 / 1 |
| C. Network code or URL in a Bash input | 7 / 5 |
| D. Network code or URL written to files | 0 / 0 |
| E-blocked, in any tool result | 55 / 54 |
| E-blocked, in the result of an A/B/C call | 54 / 53 |
| E-success, in any tool result | **0 / 0** |
| E-success, in the result of an A/B/C call | **0 / 0** |
| B calls by their own result: blocked / success / no signal | 54 / 0 / 5 |
| C calls by their own result: blocked / success / no signal | 1 / 0 / 6 |
| F. URLs: provider / PyPI / conda / localhost | 0 / 0 / 0 / 0 |
| F. URLs: code hosting / scholarly / other | 1 / 3 / 3 (in 1 / 2 / 3 runs) |

**Coverage.**

- One stream has one non-JSON line (a CLI warning); the other 343 have none.
- Two runs (A-040-s2, A-040-s3, both time-limit runs) have no final result event, so their session-level usage counters are missing. Their tool calls were scanned normally.
- One run (AX-042-s1) spawned 2 subagents, whose 122 messages are in the stream and were scanned.
- No run has a permission denial.

The one E-blocked result that is not paired with an A/B/C call is the output of a test the agent ran (AX-042-s1): a library inside the test tried to download data and got the proxy's `403 Forbidden`.

## Flagged runs

A run is flagged when it has a hit in A, B (excluding pip-local), C, E-success, or F outside the provider category. 59 runs are flagged, and 44 of them were scanned without being read.

| Runs | Reason | Counts |
|---|---|---|
| A-029-s1, A-034-s1, A-038-s3, A-040-s1, A-040-s2, A-040-s4, A-041-s1, A-041-s2, A-043-s1, A-043-s2, A-045-s1, A-046-s1, A-046-s3, A-047-s1, A-048-s1, A-048-s3, A-048-s4, A-052-s1, A-052-s3, A-054-s2, A-060-s1, A-061-s2, A-062-s1, A-062-s2, A-070-s1, A-070-s3, A-071-s1, A-079-s1, A-080-s1, A-080-s2, A-081-s1, A-081-s3, A-083-s1, A-092-s1, A-101-s1, A-104-s2, A-104-s3, A-107-s1, A-107-s2, A-107-s3, A-108-s1, A-108-s2, A-108-s3, AH-029-s1, AH-071-s1, AX-060-s1, AX-071-s1, AX-092-s1 | B | 1 `pip download` each; result blocked |
| A-061-s3 | B | 2 `pip download`; both results blocked |
| A-061-s1 | B | 2 `pip download`; 1 result blocked, 1 with no signal |
| A-070-s2, A-073-s2 | B | 1 `pip download` each; no signal in its result |
| A-014-s2 | B | 1 non-local `pip install`; result blocked |
| A-018-s1 | B | 2 non-local `pip install`/`uv`; no signal in their results |
| A-053-s1 | B, C, F | 1 curl/wget, result blocked; 2 C calls, 1 blocked and 1 with no signal; URLs: 1 code hosting, 1 scholarly |
| A-053-s3 | C, F | 2 C calls, no signal; URLs: 2 scholarly |
| A-072-s1, AX-072-s1 | C, F | 1 C call each, no signal; URL: 1 other each |
| AH-072-s1 | B, C, F | 1 `pip download`, result blocked; 1 C call, no signal; URL: 1 other |

**Where to look first:** A-018-s1, A-053-s1 and A-053-s3, the runs with network commands or URLs whose results carry no signal. Then A-061-s1, A-070-s2 and A-073-s2, which have one `pip download` each without a signal. No result in any of them contains a success string.

**What the readable runs show.** In the flagged runs that could be read:

- **`pip download`.** All 13 calls failed with `No matching distribution found`, pip's result when the package index is unreachable. Each asked for a released copy of the package under repair: 8 by name only, 5 for a specific version. The same commands also looked for an installed copy (`pip show`, an import, or a filesystem search).
- **Inline code with URLs.** The 3 C calls in the readable runs are heredocs that write a new version of one function of the package under repair, with its docstring, into a file the agent then patched the package with. The URLs (standards documents) are references in that docstring and its comments; no network request is made.

## What this shows and what it does not show

The same limits apply as for the other scans ([`network-scan.md`](network-scan.md#what-this-shows-and-what-it-does-not-show)):

- The scan sees commands and inline code in Bash inputs. Network calls made from inside programs the agent ran from files surface only through their output.
- The patterns are lexical.
- The egress proxy's access log was not kept.
- For the 44 unread flagged runs, the scan establishes only counts.

The agent records are available to the benchmark maintainers.

## Reproduce

```bash
python -I analysis/contamination_scan.py --selftest
python -I analysis/contamination_scan.py --jobs-dir <batch-1>/jobs <batch-2>/jobs ... --run-ids --csv /tmp/scan.csv
```

With the job folders of the seven batches, the output equals `analysis/out/opus-5.5-effort/contamination-scan.csv`. The batch folders also hold the job folders of the unpublished arms, which the script skips by name.
