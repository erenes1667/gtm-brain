Executed with n8n 2.44.6 (npm, Node 24, CLI: import:workflow then execute) on 2026-10-24.
Same workflow as n8n/gtm-brain-weekly.json, with two edits for the test: paths point at this repo
and a 2-domain CSV, and the CLI starts it at the "Every Monday 07:00" node (the CLI cannot fire a schedule on a clock).
Result: status success, 5 of 9 nodes executed: Every Monday 07:00, Run gtm-brain CLI, Read metrics, Parse metrics, Notify reviewer (draft only). The error branch and "Run now (manual)" did not run.
Bug found and fixed before this run: the date expressions in the workflow lacked a leading "=". The fix was made before the first commit, so git history does not show it.
