---
description: Record human approval for first lines, then export the sequence CSVs
argument-hint: [domain1,domain2 | all-passed] [out-dir]
---
Record approval for the rows the human named in `$1`, then export.

1. Only the human decides which rows are approved. If `$1` is empty, show `first_lines.csv` rows with status `pass` and ask which to approve. Do not guess.
2. Run: `uv run gtm-brain approve --out ${2:-runs/latest} --domains $1` (or `--all-passed` if the human said `all-passed`).
3. Run the export: `uv run gtm-brain export --out ${2:-runs/latest}`. The PreToolUse hook blocks this call if no row is approved.
4. Report the export counts and the paths of `export/instantly.csv` and `export/hubspot_companies.csv`. Never send anything.
