# Reviewer walk-through
1. Read the [README](../README.md) for the workflow, source-provenance split and aggregate results.
2. Inspect `pipeline/run_weekly.py` for taxonomy filtering, CRM company candidate matching and SQLite state.
3. Inspect `pipeline/cms_discovery.py` for official CMS link discovery.
4. Inspect `scripts/generate_fixtures.py` to see **fictional inputs**, not Passage Health data.
5. Open **Actions → Public demo — sanitized ABA NPPES pipeline → Run workflow**.
6. Confirm **4 → 3 → 0** new *synthetic* provider events and download `synthetic-demo` evidence.
7. Read the separately emailed confidential workbook, process documentation and deck for actual findings.

This public workflow demonstrates deterministic filtering, CRM candidate matching and SQLite idempotency; it does not prove live weekly ingestion, real CRM outcomes, or two original weekly files.
