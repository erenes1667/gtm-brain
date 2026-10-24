#!/usr/bin/env python3
"""PreToolUse hook: block export until a human approved at least one row in approvals.csv.
Stdlib only. Exit 2 blocks the tool call and shows stderr to Claude."""
import csv, json, os, sys
from pathlib import Path

YES = {"yes", "y", "true", "1", "approved"}


def is_export(payload):
    name = payload.get("tool_name", "")
    if name.endswith("export_sequence"):
        return True
    cmd = (payload.get("tool_input") or {}).get("command", "")
    return name == "Bash" and "gtm_brain" in cmd.replace("-", "_") and " export" in cmd


def out_dir(payload):
    ti = payload.get("tool_input") or {}
    cmd = ti.get("command", "")
    if "--out" in cmd.split():
        parts = cmd.split()
        return Path(parts[parts.index("--out") + 1])
    return Path(ti.get("out_dir") or os.environ.get("GTM_OUT", "runs/latest"))


def approved(path):
    p = Path(path) / "approvals.csv"
    return p.exists() and any(r.get("approved", "").strip().lower() in YES for r in csv.DictReader(p.open()))


def main():
    payload = json.load(sys.stdin)
    if is_export(payload) and not approved(out_dir(payload)):
        print(f"BLOCKED: no approved rows in {out_dir(payload)}/approvals.csv. "
              "Ask the human to review first_lines.csv, then run /gtm-approve.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
