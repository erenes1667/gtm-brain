# Deliverability checklist

`gtm-brain check-domain DOMAIN` covers the first three items. The rest are manual.

1. SPF: exactly one `v=spf1` record, ending in `-all` or `~all`, not `+all` or `?all`.
2. DKIM: a published key for the selector your sending tool uses. The tool tries common selectors only (google, selector1, selector2, k1, s1, default).
3. DMARC: a `_dmarc` record. Start at `p=none` with a report address, move to `quarantine` then `reject` once reports are clean.
4. Send from a separate domain, not the main brand domain.
5. Warm up new mailboxes slowly. Keep daily volume low until replies and bounces look normal.
6. Keep bounce rate and spam complaints under your sending tool's stated limits. Check the tool's docs for the current numbers.
7. Tag links with UTM parameters. The Instantly export does this (`utm_source=instantly`, `utm_medium=email`, `utm_campaign`).
8. Verify addresses before sending. This project does not do it: the email column is empty.
