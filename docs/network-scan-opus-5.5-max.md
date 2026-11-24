# Network and download attempts in the agent records: Claude Opus 5.5 (max)

A count-only scan of the agent records of all 119 scored Opus 5.5 runs, made on 2026-11-24 with the patterns of the Fable 5.2 scan, unchanged (method, pattern list and limits: [`network-scan.md`](network-scan.md)). Script: [`analysis/contamination_scan.py`](../analysis/contamination_scan.py). Per-run counts: [`analysis/out/opus-5.5-max/contamination-scan.csv`](../analysis/out/opus-5.5-max/contamination-scan.csv) (task IDs, counts and reason codes only).

## Summary

The agent never used its web-fetch or web-search tools, though both were available in every run. It never ran curl, wget, pip or uv installs, ssh or a system package manager. It tried `pip download` 12 times in 12 runs; every one of those attempts returned a blocked-network error. One inline network call with a PyPI URL was also blocked. The one `git clone` cloned the agent's own working directory to a temporary folder and made no network request. No result of any network attempt shows a successful download. As for the Fable run, the flagged runs are listed below by task ID and counts so that the maintainers can inspect them; 8 of them were scanned without being read.

## What was scanned

- **Scope.** The 119 scored runs. No session was set aside in this pass, so nothing else exists to cover.
- **Record.** Per run, only the agent's own session record (`agent/claude-code.txt`, Claude Code's stream-JSON). All 119 runs had it. Nothing under `verifier/` or a task's `tests/` was opened.
- **Patterns, units, flags:** identical to the Fable scan. The script's only change is that it accepts `OX-<task>-s1` job folders; run on the Fable job folders, it reproduces `analysis/out/contamination-scan.csv` exactly. The 151 self-checks passed before the scan.
- **Reading.** For most runs only counts and task IDs left the script. For the rest, the matched lines were read to describe what happened (summarised below without task IDs).

## Totals over the 119 runs

Each cell is calls (or results) / runs with at least one.

| Category | All 119 runs |
|---|---|
| A. WebFetch / WebSearch tool calls, server web blocks, usage web counters | **0 / 0** |
| B. Shell network commands (excluding pip-local) | 13 / 13 |
| of which `pip download` | 12 / 12 |
| of which `git clone/fetch/pull` | 1 / 1 (a clone of the local working directory) |
| non-local `pip install` / `uv`, curl, wget, conda/npm/apt/cargo/go, svn/hg, ssh/scp/nc/telnet | 0 / 0 |
| B-pip-local | 0 / 0 |
| C. Network code or URL in a Bash input | 1 / 1 |
| D. Network code or URL written to files | 18 / 10 |
| E-blocked, in any tool result | 15 / 14 |
| E-blocked, in the result of an A/B/C call | 13 / 13 |
| E-success, in any tool result | 1 / 1 |
| E-success, in the result of an A/B/C call | **0 / 0** |
| B calls by their own result: blocked / success / no signal | 12 / 0 / 1 |
| C calls by their own result: blocked / success / no signal | 1 / 0 / 0 |
| F. URLs: provider / PyPI / conda / localhost | 0 / 1 / 0 / 0 |
| F. URLs: code hosting / scholarly / other | 0 / 0 / 0 |

Coverage: 7 streams have one non-JSON line (a CLI warning), the other 112 none. Four runs (001, 014, 033, 040, the time-limit runs) have no final result event, so their session-level usage counters are missing; their tool calls were scanned normally. Nine runs spawned 17 subagents in total, whose 1,037 messages are in the stream and were scanned. One run has one permission denial. The `pip download` calls name packages, not URLs, so they do not count toward F.

## Flagged runs

A run is flagged when it has a hit in A, B (excluding pip-local), C, E-success, or F outside the provider category. 14 runs are flagged; 8 of them were scanned without being read.

| Task | Reason | Counts |
|---|---|---|
| 020, 040, 047, 054, 056, 065, 076, 081, 092, 098, 100 | B | 1 `pip download` each; result blocked |
| 061 | B, E-success | 1 `pip download`, result blocked; 1 tool result with a success string, **not** from an A/B/C call (the same task had an unpaired success string in the Fable scan) |
| 071 | B | 1 `git clone`; no blocked or success signal in its result |
| 090 | C, F | 1 C call with a PyPI URL; result blocked |

**Where to look first:** 061 (an unpaired success string, in both runs of this task) and 090 (an inline call to PyPI, blocked).

**What the readable runs show.** In the flagged runs that could be read:

- Every `pip download` (5 calls) failed with `No matching distribution found`, pip's result when the package index is unreachable. One asked for a specific released version of the package under repair; two asked for a linter; two plainly tested whether the network or the index was reachable (`pip download nothing-here`, a request for version `0.0`).
- The one `git clone` was `git clone -q . /tmp/<folder>`: the agent cloned its own working directory to check that its patch applies to a clean copy. It made no network request.

## What this shows and what it does not show

The same limits apply as for the Fable scan ([`network-scan.md`](network-scan.md#what-this-shows-and-what-it-does-not-show)): the scan sees commands and inline code in Bash inputs, not network calls made from inside programs the agent ran from files (those surface only through their output); the patterns are lexical; the egress proxy's access log was not kept; and for the 8 unread flagged runs the scan establishes only counts. The agent records are available to the benchmark maintainers.

## Reproduce

```bash
python -I analysis/contamination_scan.py --selftest
python -I analysis/contamination_scan.py --jobs-dir <run-dir>/jobs --csv /tmp/scan.csv   # counts and task IDs only
```

With the Opus job folders, the output should equal `analysis/out/opus-5.5-max/contamination-scan.csv`.
