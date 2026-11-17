# Network and download attempts in the agent records

A count-only scan of the agent records of all 119 scored runs, made on 2026-11-17 with patterns fixed before scanning. Script: [`analysis/contamination_scan.py`](../analysis/contamination_scan.py). Per-run counts: [`analysis/out/contamination-scan.csv`](../analysis/out/contamination-scan.csv) (task IDs, counts and reason codes only).

## Summary

We scanned the agent records of all 119 scored Claude Fable 5.2 (xhigh) runs on SWE-bench Science for network or download attempts, using patterns fixed before scanning. Most of these transcripts belong to a held-out research set, so the scan was count-only for them. The runs were configured with an egress allowlist: the agent could reach only the model provider through an authenticating proxy, and the verifier had no network. The agent never used its web-fetch or web-search tools, though both were available. It never ran curl, wget, git clone/fetch/pull, ssh or a system package manager. It did try `pip download` 20 times across 19 runs, several times asking for a specific released version of the package it was repairing. Every one of those attempts returned a blocked-network error (in the runs we could read, the package index was unreachable), and no result of any network attempt shows a successful download. The scan cannot see network calls made from inside scripts or libraries the agent ran from files, except through their printed output; in the one such case we could read, the proxy refused the connection. The flagged runs are listed below by task ID and counts, so that the maintainers can inspect them directly; 14 of them were scanned without being read.

## What was scanned and how

- **Scope.** The 119 scored runs only. Sessions that were set aside and rerun from scratch were never scored and are not covered.
- **Record.** Per run, only the agent's own session record (`agent/claude-code.txt`, Claude Code's stream-JSON). All 119 runs had it. Nothing under `verifier/` or a task's `tests/` was opened.
- **Unit.** A, B, C and D count tool calls; E counts tool results; F counts B or C calls with at least one URL in a host category. Calls made inside subagents are in the stream and were scanned too.
- **Reading.** For most runs only counts and task IDs left the script. For the rest, the matched lines were read to describe what happened (summarised below without task IDs).

| | Pattern (full lists in the script) |
|---|---|
| **A. Web tools** | `WebFetch` / `WebSearch` tool calls, server-side web tool blocks, and the web-request counters in Claude Code's usage reports |
| **B. Shell network commands** | at a command position in a Bash call: `curl`, `wget`, `git clone/fetch/pull/ls-remote/submodule update`, `pip`/`uv` install or download, `conda`/`mamba`/`npm`/`yarn`/`apt`/`cargo`/`go` installs, `svn`/`hg` checkouts, `ssh`/`scp`/`nc`/`telnet`. pip installs of local paths only are counted separately (B-pip-local) |
| **C. Network code run inline** | Bash input containing `requests.get/post`, `urllib.request`, `urlopen`, `httpx.`, `http.client`, `socket.*`, `aiohttp`, or an `http(s)://` URL |
| **D. Network code written to files** | the same strings in Write/Edit inputs (weak evidence: source code often has URLs in docstrings) |
| **E. Outcome signals** | blocked (`ERR_ACCESS_DENIED`, `403 Forbidden`, `Could not resolve host`, `No matching distribution found`, ...) or success (`Downloading http`, `Saving to:`, `HTTP/1.1 200`, `Receiving objects:`, a clean `Cloning into`) in a tool result |
| **F. Host categories** | of URLs in B or C calls: model provider, PyPI, conda, code hosting, scholarly, localhost, other |

The script runs 151 synthetic self-checks before every scan. Two implementation bugs found by the self-check were fixed before any record was read; after the first full run, two reporting-only columns were added (the pip subtype split and the per-call outcome cross-tab). Matching and flags were not changed after results were seen.

## Totals over the 119 runs

Each cell is calls (or results) / runs with at least one.

| Category | All 119 runs |
|---|---|
| A. WebFetch / WebSearch tool calls, server web blocks, usage web counters | **0 / 0** |
| B. Shell network commands (excluding pip-local) | 23 / 20 |
| of which `pip download` | 20 / 19 |
| of which non-local `pip install` / `uv` | 3 / 1 |
| curl, wget, git, conda/npm/apt/cargo/go, svn/hg, ssh/scp/nc/telnet | 0 / 0 |
| B-pip-local | 0 / 0 |
| C. Network code or URL in a Bash input | 7 / 6 |
| D. Network code or URL written to files | 4 / 4 |
| E-blocked, in any tool result | 24 / 20 |
| E-blocked, in the result of an A/B/C call | 20 / 19 |
| E-success, in any tool result | 1 / 1 |
| E-success, in the result of an A/B/C call | **0 / 0** |
| B calls by their own result: blocked / success / no signal | 20 / 0 / 3 |
| C calls by their own result: blocked / success / no signal | 0 / 0 / 7 |
| F. URLs: provider / PyPI / conda / localhost | 0 |
| F. URLs: code hosting / scholarly / other | 1 / 2 / 4 |

Coverage: every stream has exactly one non-JSON line (a CLI warning). Three runs (062, 107, 108, the time-limit runs) have no final result event, so their session-level usage counters are missing; their tool calls were scanned normally. One run (119) spawned one subagent, whose 67 messages were scanned. No permission denials. F-PyPI is 0 although there were 20 `pip download` calls, because those commands name a package, not a URL.

## Flagged runs

A run is flagged when it has a hit in A, B (excluding pip-local), C, E-success, or F outside the provider category. 26 runs are flagged; 14 of them were scanned without being read.

| Task | Reason | Counts |
|---|---|---|
| 018 | B | 3 non-local `pip install`/`uv` calls; **no blocked or success signal** in their results |
| 020, 026, 038, 039, 046, 052, 066, 080, 083, 088, 092, 098, 100, 103, 107, 113, 116 | B | 1 `pip download` each; result blocked |
| 114 | B | 1 `pip download`, result blocked (plus 3 more blocked results from other calls) |
| 055 | B, C, F | 2 `pip download` (both blocked); 1 C call (no signal); URL: 1 scholarly |
| 053 | C, F | 2 C calls (no signal); URLs: 1 code hosting, 1 scholarly |
| 056, 057, 071 | C, F | 1 C call each (no signal); URL: 1 other |
| 072 | C, F | 1 C call (no signal); URL: 1 other; 1 blocked result from another call |
| 061 | E-success | 1 tool result with a success string, **not** from an A/B/C call |

**Where to look first:** 018 (three install calls with no outcome signal: local installs the narrow pip-local rule did not recognise, or remote installs with suppressed output); 053, 055 and 056 (URLs in Bash inputs, including a code-hosting URL in 053); 061 (an unpaired success string).

**What the readable runs show.** In the flagged runs that could be read:

- Every `pip download` (9 calls) failed with pip's `Could not find a version that satisfies the requirement ... (from versions: none)` / `No matching distribution found`, its result when the package index is unreachable. In five of them the agent asked for a specific released version of the package under repair or a close dependency; two (`pip download nothing`) plainly tested whether the network was reachable.
- One probe script, written with a heredoc and then run, called a library function that tries to download test data. The proxy refused the tunnel (`Tunnel connection failed: 403 Forbidden`). B and C cannot see this kind of call; only its blocked outcome (E) did.
- The C/F hits were URLs inside docstrings or licence headers of source code piped through a heredoc. They made no request.

## What this shows and what it does not show

It shows that the agent never called WebFetch or WebSearch, never ran curl, wget, git clone/fetch/pull, ssh or a system package manager, and that no result of a network call contains a success signal. Every `pip download` result contains a blocked-network string.

It does not show:

- **Network calls inside programs.** The scan sees commands and inline code in Bash inputs, not calls made from inside scripts or libraries the agent ran from files. Those surface only through their output (E); suppressed or truncated output goes uncounted.
- **Patterns outside the fixed lists.** The patterns are lexical. For example, current pip prints `Downloading pkg.whl` without the URL.
- **Proxy-side proof.** The egress proxy's access log lived inside its container and was not kept. This is evidence from the agent's own record of what it tried and what it was told.
- **The 14 unread flagged runs.** For these the scan establishes only counts. Someone allowed to read them has to say what happened; the records are available to the benchmark maintainers.

## Reproduce

The agent records are not published, so this needs a local copy of the job folders:

```bash
python -I analysis/contamination_scan.py --selftest
python -I analysis/contamination_scan.py --jobs-dir <run-dir>/jobs --csv /tmp/scan.csv   # counts and task IDs only
```

The output should equal `analysis/out/contamination-scan.csv`.
