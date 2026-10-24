# gtm-brain

A Claude Code plugin, MCP server and CLI that turn a list of company domains into checked opening lines, and export only what a human approved.

**Personal project, synthetic data.** The ICP and offer are synthetic. The inputs are the public homepages of 25 DTC brands, company level only. No people, no emails. No employer or client code, data or names were used.

Live demo: https://erenes1667.github.io/gtm-brain/ (served from `docs/`). Repo: https://github.com/erenes1667/gtm-brain. Interview prep: `docs/INTERVIEW.md`.

## How it works

```
domains.csv
  -> fetch_site            robots.txt, cache, homepage + 1 about/collections page
  -> extract_company_profile   Haiku + platform signals from HTML rules
  -> score_icp             YAML rules (0-60) + Haiku judgment (0-40), tiers A/B/C
  -> write_first_line      Sonnet, A and B only: one line + verbatim evidence quote
  -> gates                 1 banned phrases/dashes/length  2 quote is verbatim in fetched text
                           3 claim checker (Haiku), fails closed. One rewrite, else dropped
  -> approvals.csv         a human marks rows
  -> PreToolUse hook       blocks export with no approved row
  -> export_sequence       export/instantly.csv + export/hubspot_companies.csv
```

The diagram with colors is in `docs/index.html`.

## Quickstart

```bash
uv sync
uv run pytest -q                                   # offline, LLM mocked, no key needed
cp .env.example .env                               # add your key, see below
uv run gtm-brain run domains.csv --out runs/my-run   # the CLI reads ./.env itself
uv run gtm-brain approve --out runs/my-run --domains allbirds.com,buffy.co
uv run gtm-brain export  --out runs/my-run
uv run gtm-brain cost    --out runs/my-run
```

Only `run` needs a key. `approve`, `export`, `cost` and `check-domain --help` work without one. To try them without changing tracked files, point `--out` at your own folder (as above) or copy a committed run first: `cp -r runs/2026-10-24-live-v2 runs/try && uv run gtm-brain approve --out runs/try --domains allbirds.com`.

`.env` needs `ANTHROPIC_API_KEY_PERSONAL` and `ANTHROPIC_WORKSPACE_ID_PERSONAL` (sent as the `anthropic-workspace-id` header). Rename them in `gtm_brain/llm.py` if you use a plain key. The spend cap is `GTM_BUDGET_USD` (default 6), checked against `runs/ledger.jsonl` before each call.

### Install as a Claude Code plugin

```
/plugin marketplace add /path/to/gtm-brain
/plugin install gtm-brain@gtm-brain-local
```

You get the skills `gtm-research`, `icp-scoring`, `first-lines`, the commands `/gtm-run` and `/gtm-approve`, the MCP server `gtm-brain` (seven tools) and the approval hook. `claude plugin validate plugin` passes with one icon warning (docs/plugin-validate.txt). Run Claude Code from the repo root so `.env` and `runs/` resolve.

## Results (live run 2026-10-24)

From `runs/2026-10-24-live/metrics.json` and `evals/checker_results.json`.

| Measure | Value |
|---|---|
| Accounts | 25 (19 readable, 6 blocked or failed) |
| Tiers A / B / C | 11 / 7 / 7 |
| Lines attempted / kept | 18 / 17 |
| Same 25 domains re-run with the shipped checker prompt (`runs/2026-10-24-live-v2/`) | 14 of 18 first try (78%), 18 of 18 kept, 0 dropped, $0.4630. Pages came from cache, the writer produced new lines. The 94% row below is from the first prompt. |
| Passed all gates on first try (first checker prompt) | 17 of 18 (94%) |
| Cost total / per account / per approved line | $0.4114 / $0.0165 / $0.0242 |
| Cost by model | Haiku $0.1261, Sonnet $0.2853 |
| LLM calls | 76 |
| Time per account / wall | 4.69 s / 31.0 s (4 workers) |
| Held-out v1, 19 new domains, first checker prompt | 13 of 13 lines passed first try. Hand labels: 12 faithful, 1 adds words (`evals/real_lines_labeled.jsonl`). $0.3318, `runs/2026-10-24-heldout/metrics.json` |
| Held-out v2, same 19 domains, shipped checker prompt | 9 of 11 lines passed first try, 10 of 11 kept, 1 dropped. My read of the 10 kept lines: all faithful (`evals/heldout_v2_labels.jsonl`, same single labeler). Pages were fetched again and the writer produced new lines, so this is a fresh sample. $0.3390, `runs/2026-10-24-heldout-v2/metrics.json` |
| Claim checker on 24 labeled synthetic cases | 24 correct, 0 false pass, 0 false fail |
| Claim checker on 30 real lines, hand labeled by the author, first prompt | Passed all 30. I label 24 faithful and 6 as adding words beyond the quote, so it caught 0 of 6. One labeler, strict reading. `evals/real_lines_labeled.jsonl`, `evals/real_lines_summary.json` |
| Same 30 lines, tightened prompt (shipped) | Catches 5 of 6 padded lines, wrongly fails 2 of 24 faithful lines. Synthetic cases: 0 false pass, 1 false fail. Tuned on the same labels, so in-sample. A stricter first draft caught 6 of 6 but failed 10 of 24 faithful lines. `evals/real_lines_rescored.json`, `evals/real_lines_rescored_strict.json`, cost $0.0564 in `evals/rescore_cost_log.jsonl` |
| n8n workflow executed once | n8n 2.44.6, 2 domains, status success, cost $0.0441. `runs/2026-10-24-n8n/` |
| All project spend (runs, evals, smoke tests) | $3.49 of the $6 cap, from `runs/ledger.jsonl` |

Run history on the same domains (each folder under `runs/` has its own metrics):

| Run | First-try pass | Lines kept | Cost |
|---|---|---|---|
| v1 baseline | 22% | 9 of 18 | $0.6827 |
| v2 thinking disabled (Haiku) or between_tools (Sonnet) | 0% | 7 of 18 | $0.6827 |
| v3 final (first checker prompt) | 94% | 17 of 18 | $0.4114 |
| v3 re-run, shipped checker prompt | 78% | 18 of 18 | $0.4630 |

v1 and v2 both total $0.6827 by coincidence. Their per-model figures differ, see each `metrics.json`. In v1 thinking was off for Haiku only.

Costs are token counts times the assumed rates in `pricing.yaml`. Edit them to match your console.

## Design notes

- **Evidence gate in code.** The model must quote the page. Code checks the quote is verbatim. A Haiku checker then compares the line to the quote. Both reduce invented facts. Neither guarantees none: the live glossier.com line added "for makeup" beyond its quote and passed.
- **Checker fails closed.** An unparseable verdict counts as a fail.
- **Model split.** Haiku reads and judges. Sonnet writes. Thinking is `disabled` for Haiku. Sonnet 5.5 rejected `disabled`, so it is set to `between_tools` (the value the API error named). I believe unrestricted thinking is why the v1 Sonnet writer returned no text for 7 of 18 accounts; the run shows only the empty rows, so that cause is my reading.
- **Approval outside the model.** The hook and `export_sequence` both refuse to export without a yes in `approvals.csv`.
- **Rules before LLM.** ICP rules live in `icp.yaml` and are unit tested. The LLM adds judgment and reasons.
- **Polite fetching.** robots.txt, honest user agent, two pages per domain, cache, one retry on 429.

## CRM, deliverability and tracking

- `gtm-brain lifecycle --out RUN --accounts accounts.csv` tags accounts new, waiting, stale (over 30 days) or replied. Stale accounts get a follow-up draft built from the verified line, only if the account is approved. No LLM call, nothing is sent. Example: `runs/2026-10-24-lifecycle/` (synthetic dates).

- `gtm-brain hubspot --out RUN` upserts approved companies by domain. Dry run is the default and writes `export/hubspot_dry_run.json`. `--live` needs `HUBSPOT_TOKEN` and the `gtm_*` company properties. The client is written and unit-tested against recorded payloads, never run against a live portal.
- `gtm-brain check-domain DOMAIN` reads SPF, DMARC and common DKIM selectors with `dig`. Read only. See `docs/deliverability-checklist.md`.
- The Instantly export adds UTM parameters to the website field and a `utm_campaign` column.
- `docs/build-vs-buy.md` compares build cost with Clay list prices.

No endorsement is implied. Brand names belong to their owners and appear only because their public homepages were read.

## Files

`gtm_brain/` code, `plugin/` Claude Code plugin, `icp.yaml`, `banned.txt`, `domains.csv`, `tests/` (47 offline tests), `evals/` checker cases, results and hand-labeled real lines, `runs/` real run artifacts (`profiles.jsonl`, `scores.csv`, `first_lines.csv`, `approvals.csv`, `export/`, `cost_log.jsonl`, `metrics.json`), `n8n/gtm-brain-weekly.json`, `.github/workflows/test.yml`.

Page shots in `docs/` are full-page (1440x9800 and 390x17700). The page has two em dashes, both inside one verbatim Allbirds quote, and they are the source's.

## Limits

- The n8n workflow ran once (2 domains, `runs/2026-10-24-n8n/`): 5 of 9 nodes executed, starting from the "Every Monday 07:00" node as the CLI start node. The schedule did not fire on a clock. The error branch and "Run now (manual)" did not run.
- No CRM sync was run against a real HubSpot portal, and there is no Salesforce path. The HubSpot client is written and unit-tested against recorded payloads; its payloads are written from HubSpot's public CRM v3 companies API (search by domain, then create or patch) and were not checked against a live portal. Re-runs avoid duplicates by searching on `domain` before create. Instantly import is CSV only.
- Company-level enrichment reads only the HTML already fetched (`gtm_brain/enrich.py`): platform, email/SMS, reviews, helpdesk and analytics tools from script sources, and whether a careers link exists. It is rule based and can miss tools loaded late by a tag manager. It was added after the live and first held-out runs, so only `runs/2026-10-24-heldout-v2/` has it. Contact enrichment is not built, on purpose. The export `email` column stays empty so the repo holds no personal data; a waterfall tool (see `docs/build-vs-buy.md`) would fill it.
- Deliverability is read-only: SPF, DMARC and DKIM lookups, plus UTM tags. No warmup, bounce or inbox-placement tracking.
- An unreachable robots.txt (network error) is treated as absent. A robots.txt that returns 5xx is treated as blocked.
- Lines can add small words beyond their quote and still pass. By my hand labels 6 of 30 passed lines did (glossier.com, harrys.com, ritual.com, buffy.co, ridge.com, girlfriend.com). The first checker prompt caught none; the tightened prompt catches 5 and misses buffy.co, at the price of failing 2 of 24 faithful lines. The live run and held-out v1 were made with the first prompt. Held-out v2 used the shipped prompt. Treat the checker as a filter, not a guarantee.
- The held-out runs are 13 and 11 lines. It is a small sample, not a tight range.
- The final prompt was tuned on the same 25 domains, so 94% is in-sample from one run. The held-out rows above are the unbiased check.
- Six domains could not be read (two 429, three 403, one robots disallow). They are skipped, not worked around.
- Lines restate a homepage sentence. No trigger events, no reply-rate data.
- The 24-case checker eval is easy and written by the author. The 30 real-line labels have one labeler (me), so they are my read, not ground truth.
- Export has an empty `email` column. Fill it from an enrichment tool.
- The approval step in the demo transcript was done by the builder with a flag.
- Some pages name founders. Filter names before real use.
