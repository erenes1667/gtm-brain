"""CLI: the same pipeline the plugin drives. gtm-brain run|approve|export|cost"""
import argparse, json, sys
from pathlib import Path

from . import pipeline
from .approvals import approve
from .export import export_sequence, NotApproved
from .llm import LLM, require_keys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gtm-brain")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("domains_csv"); r.add_argument("--out", required=True)
    r.add_argument("--icp", default="icp.yaml"); r.add_argument("--ledger", default="runs/ledger.jsonl")
    a = sub.add_parser("approve"); a.add_argument("--out", required=True)
    a.add_argument("--domains", default=""); a.add_argument("--all-passed", action="store_true")
    e = sub.add_parser("export"); e.add_argument("--out", required=True)
    h = sub.add_parser("hubspot"); h.add_argument("--out", required=True); h.add_argument("--live", action="store_true")
    lc = sub.add_parser("lifecycle"); lc.add_argument("--out", required=True); lc.add_argument("--accounts", required=True)
    d = sub.add_parser("check-domain"); d.add_argument("domain")
    c = sub.add_parser("cost"); c.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "run":
        try:
            require_keys()
        except RuntimeError as ex:
            print(f"ERROR: {ex}", file=sys.stderr); return 1
        out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
        print(json.dumps(pipeline.run(args.domains_csv, out, LLM(args.ledger, out / "cost_log.jsonl"), args.icp), indent=2))
    elif args.cmd == "approve":
        import csv
        out = Path(args.out)
        if args.all_passed:
            ds = {x["domain"] for x in csv.DictReader(open(out / "first_lines.csv")) if x["status"] == "pass"}
        else:
            ds = {d.strip() for d in args.domains.split(",") if d.strip()}
        print(json.dumps({"approved_rows": approve(out, ds)}))
    elif args.cmd == "export":
        try:
            print(json.dumps(export_sequence(args.out)))
        except NotApproved as ex:
            print(f"BLOCKED: {ex}", file=sys.stderr); return 2
    elif args.cmd == "hubspot":
        from .hubspot import push_companies
        print(json.dumps(push_companies(args.out, live=args.live)))
    elif args.cmd == "lifecycle":
        from .lifecycle import run_lifecycle
        print(json.dumps(run_lifecycle(args.out, args.accounts)))
    elif args.cmd == "check-domain":
        from .deliverability import check_domain
        print(json.dumps(check_domain(args.domain), indent=2))
    elif args.cmd == "cost":
        print(json.dumps(pipeline.cost_report(args.out), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
