# Notice: third-party sources and what is not included

Nothing in this repository relicenses third-party material. Our own code is MIT (`LICENSE`); our data and documentation are CC BY 4.0 (`LICENSE-DATA.md`).

## Third-party inputs used here

| Input | Owner and terms | How it is used |
|---|---|---|
| SWE-bench Science dataset, `data/tasks.csv` (Hugging Face `OpenMOSS-Team/SWE-bench-Science`, revision `997408298e8e4d09978b1120b95c4540d1a71bcb`) | OpenMOSS; dataset metadata and tooling under the MIT licence. Task content, source snapshots and images keep their upstream licences | Metadata columns only, copied into `results/per-task.csv`: `title`, `domain`, `language`, `license_gate`, `restricted_license`, `science_knowledge_ablation`, whether `material_license` is set, and membership of `selections/default-96.json`. Image references with digests from each task's `task.toml` in `provenance/per-task-provenance.jsonl` |
| Paper: Xu, Lu, Zheng, Wang, Qiu, "SWE-bench Science: Can Coding Agents Resolve Engineering Tasks in Science?", arXiv 2608.19799v2 | the authors; CC BY 4.0 | Domain label per task from Table 5 (`analysis/data/paper-domains.csv`, `paper_domain` column); definitions and published numbers quoted with citation |
| Leaderboard site (`github.com/swescience/swescience.github.io`, <https://swescience.github.io>) | the benchmark maintainers; **no licence file** | Not redistributed. `analysis/fetch_inputs.py` downloads the data files from commit `f16153e5c47c46b2f6f2ebf0aaefae34bdf8c8bd` for local analysis. Published aggregate figures (17 configurations, `analysis/out/chart-leaderboard.csv`, the figures, the README tables) are quoted with their source. Per-task comparison tables that contain other configurations' results are regenerated locally and not committed |
| SWE-bench Science code (`github.com/OpenMOSS/SWE-bench-Science`) | OpenMOSS; MIT | `harness/environment.py` subclasses its `ScienceBenchDocker` (`scripts/pier_network.py`), imported at runtime from the downloaded dataset; no code is copied |
| Pier (`datacurve-pier==0.3.0`) | Datacurve; see its package licence | Installed from PyPI; not copied |

## Not included, and why

- **Task content**: instructions, source snapshots, supplied papers, fixtures and parameter files. They belong to their upstream owners; 23 tasks carry GPL-family, non-commercial or otherwise restricted terms.
- **Hidden tests and verifier output**: no file from a trial's `verifier/` folder or a task's `tests/` folder, no per-test results, no verifier logs. Only pass counts (from `reward.json`) are published, as on the leaderboard. Counts of the unpatched base and anything derived from them are also left out.
- **Agent transcripts and patches**: they quote task content (including restricted-licence code and materials), and the passing patches would put benchmark solutions online. The SHA-256 of every patch is in `results/artefact-checksums.csv`; patches and transcripts are available to the benchmark maintainers on request.
- **Account and session data** of the agent sessions, credentials and server details.
- **Sessions that were never scored**: sessions cut off by the usage limit or by the server shutdown (rerun from scratch) and a few max-effort sessions from before the switch to xhigh.
