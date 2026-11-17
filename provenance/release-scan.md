# Pre-release scan

Result of the private pre-release scanner over every file of this repository's tree (the report itself excluded).
The scanner and its list of personal strings are kept outside the repository, so that the list is not published.

**Result: 0 findings** in 45 files (1,190,585 bytes).

| Check | Rule | Findings |
|---|---|---|
| `secret-anthropic` | Anthropic API key or OAuth token prefix | 0 |
| `secret-env` | credential variables assigned in env-file syntax | 0 |
| `secret-header` | HTTP authorisation headers and bearer tokens | 0 |
| `secret-other` | other common key formats (GitHub, Hugging Face, AWS, private keys, Slack, router keys) | 0 |
| `path-home` | home-directory, root and temporary-folder paths | 0 |
| `path-server` | the raw server run root | 0 |
| `email` | e-mail addresses | 0 |
| `ipv4` | IPv4 addresses other than the unspecified and loopback addresses | 0 |
| `ipv6` | IPv6 addresses | 0 |
| `internal-router` | mentions of the model-routing service used during development | 0 |
| `internal-experiments` | names of the author's other experiments, task-split files and project-internal paths | 0 |
| `internal-session` | Claude Code session links and ids | 0 |
| `other-model` | mentions of the other Claude model version under separate study (no data from it may appear) | 0 |
| `limit-text` | usage-limit message text and subscription plan names | 0 |
| `hidden-test-names` | names of verifier output files, outside the statement that they were never opened | 0 |
| `personal` | personal identifiers: names, account, machine and server identifiers (16 patterns from a local, unpublished list; case-insensitive) | 0 |
| `token-hash` | exact match of any token-like string (24+ characters, 2243 checked) against SHA-256 hashes of the real credential | not run: no credential hash supplied |
| `instruction-text` | any 12-word sequence shared with the 119 task instructions (18,546 sequences; sequences that are part of a published task title excluded) | 0 |
| `png-metadata` | text or EXIF chunks in PNG files | 0 |
| `hygiene-*` | symlinks; files over 1 MB; names such as `.DS_Store`, `__pycache__`, `.claude`, `verifier`, `tests`, `agent`, `model.patch`, `trajectory.json`, `reward.json`, `exception.txt`, `instruction.md` | 0 |
| `format` | every `.json`/`.jsonl` parses, every `.csv` reads, every `.py` compiles | 0 |

Allowed matches (expected, reviewed):

- `email` in `analysis/contamination_scan.py` (2): synthetic self-test URLs (user-name syntax in git URLs)
- `hidden-test-names` in `README.md` (3): statement that these files were never opened
- `other-model` in `README.md` (1): changelog line naming a planned run; no data
- `personal-authorship` in `CITATION.cff` (2): author name/account in an authorship phrase
- `personal-authorship` in `LICENSE` (1): author name/account in an authorship phrase
- `personal-authorship` in `LICENSE-DATA.md` (3): author name/account in an authorship phrase
- `personal-authorship` in `README.md` (2): author name/account in an authorship phrase
- `personal-authorship` in `leaderboard-format/README.md` (1): author name/account in an authorship phrase
- `personal-authorship` in `leaderboard-format/task-matrix-entry.json` (119): author name/account in an authorship phrase

Not covered by this scan: anything outside the files listed above (for example git history; the
repository is created fresh from this tree). The scan is lexical; it complements, and does not replace,
the whitelist build of every data file and a human review.
