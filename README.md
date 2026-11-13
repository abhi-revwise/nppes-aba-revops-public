# NPPES ABA RevOps Pipeline — Public Demonstration

A **sanitized, reproducible demonstration** of NPPES-based ABA provider discovery, matching, scoring and cross-run deduplication. **All demo NPI identifiers, names, addresses and CRM records are fictional.**

**Verified GitHub-hosted run:** [Public demo Run #3 — success](https://github.com/abhi-revwise/nppes-aba-revops-public/actions/runs/43390833804) (unit tests passed; synthetic evidence artifact `synthetic-demo-3`).

## Run the public demo

[GitHub Actions → Public demo](https://github.com/abhi-revwise/nppes-aba-revops-public/actions/workflows/public_demo.yml): choose **Run workflow**, or run locally:

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 scripts/demo_three_runs.py
```

The workflow creates synthetic NPPES-style weekly archives and a synthetic CRM, then runs the Python + SQLite pipeline across three stages: **4 new → 3 new → 0 new on repeat**. These are fictional proof-of-mechanism figures, **not** Passage Health results.

## Pipeline stages

1. Download/ingest CMS NPPES weekly V2 files (the offline demo uses synthetic CSV-in-ZIP files).
2. Filter enumeration dates and ABA taxonomies across all 15 taxonomy slots.
3. Deduplicate by NPI; distinguish organizational and individual registrations.
4. Produce **provisional** CRM match candidates, provider scores and review holds.
5. Save previously seen NPIs in SQLite so already observed providers do not appear as new.
6. Export QA and CRM-review staging; **do not automatically write to HubSpot**.

## Original case study results (not published as row-level data)

The full nonpublic analysis yielded **2,779 ABA-related NPIs** from the authentic Nov 2–8, 2026 CMS V2 weekly incremental, plus **2,730** reconstructed retrospectively from a Nov 9 monthly snapshot (Oct 26–Nov 1 enumeration window). **These are not two original weekly source files.** After revised supervised-credential and CRM-action rules: **370 net-new account candidates**, **824 new contact candidates**, **55 already-in-CRM candidates**, **4,260 market-signal-only observations**. These are provisional classifications, not verified CRM imports. Private supporting evidence and submitted workbook are shared with the case-study reviewers separately.

## Data protection

This public repository intentionally excludes all original Passage Health CRM exports, provider-level prospect output, case-study workbook, and raw CMS archive. It was created with **clean Git history**, separate from the archived private repository. Synthetic NPI placeholders are not valid actual registry identifiers. Read [data safeguards](docs/SECURITY_BOUNDARY.md) and [reviewer guide](docs/REVIEWER_GUIDE.md).

## Implementation map

- `pipeline/run_weekly.py`: 15-slot taxonomy filter, matching, scores, SQLite dedup and CSV exports.
- `pipeline/decision_layer.py`: restricted supervised-provider classification and CRM action rules for sanitized demo.
- `scripts/generate_fixtures.py`: fictional two-week NPPES + CRM fixtures.
- `scripts/demo_three_runs.py`: executes both weeks and repeat-run assertion.
- `scripts/classify_demo_actions.py`: applies public action-layer rules to fake outputs.
- `tests/`: deterministic QA and policy tests.
- `.github/workflows/public_demo.yml`: on-demand and push-triggered CI.
- `pipeline/cms_discovery.py`: production-oriented CMS webpage discovery (not used by offline public demo).

The scheduled live download and durable cross-run hosted state from the private project have **not** been independently verified. The public workflow proves the offline processing/deduplication mechanism, not live unattended CMS ingestion.
