---
description: Run the research-to-first-line pipeline on a CSV of company domains
argument-hint: <domains.csv> [out-dir]
---
Run the gtm-brain pipeline on `$1` (CSV with a `domain` column). Output dir: `$2`, default `runs/latest`.

1. Use the `gtm-research` skill. Run: `uv run gtm-brain run $1 --out ${2:-runs/latest}`.
2. Read `metrics.json` and `scores.csv` in the output dir. Report: accounts, tier counts, first-try pass rate, total cost.
3. Show the first 5 rows of `first_lines.csv` with their evidence.
4. Stop. Tell the human to review `first_lines.csv` and run `/gtm-approve`. Do not export.
