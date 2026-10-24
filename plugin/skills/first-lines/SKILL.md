---
name: first-lines
description: Write and check one-sentence personalized opening lines for outbound, each tied to a verbatim evidence quote. Use after ICP scoring, before approval and export.
---
# first-lines

`write_first_line(domain)` runs four gates. A line must pass all of them:

1. Banned-phrase filter (`banned.txt`), no dashes, max 30 words.
2. The evidence quote is a verbatim substring of the fetched page text.
3. A Haiku claim checker confirms every fact in the line is in the evidence.
4. One rewrite is allowed with the checker's complaints. After that the line is dropped.

Never write a line by hand to get around a failed gate. A dropped account stays dropped. Lines are drafts: the human approves them in `approvals.csv` before export (`/gtm-approve`).
