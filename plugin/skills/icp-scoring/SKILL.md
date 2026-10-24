---
name: icp-scoring
description: Score companies against the ICP file. Use after profiles exist, or when the human wants to change ICP rules, weights or tiers.
---
# icp-scoring

Scores live in `icp.yaml`: rule points (cap 60) plus an LLM judgment (0 to 40) with written reasons. Tiers: A at 70, B at 50, else C.

- Run `score_icp(domain)` for one company, or read `scores.csv` for a run.
- To change fit, edit rules in `icp.yaml`, not the prompt. Rules are testable offline (`uv run pytest tests/test_icp.py`).
- Always show the human the `reasons` column next to the tier. A tier without reasons is not an answer.
- Only A and B accounts get first lines.
