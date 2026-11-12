#!/usr/bin/env python3
"""Fail a CI job when a kedro-quality-check result is not good enough.

Usage:
  gate.py RESULTS_JSON [--min-score N] [--baseline BASE_JSON] [--markdown FILE]

Checks (each one is optional):
  --min-score N     overall score must be at least N (0-100)
  --baseline FILE   no criterion may be 'fail' now that was not 'fail' in FILE, and none may
                    get worse (pass -> mixed/fail, mixed -> fail). Criteria missing from the
                    baseline are treated as new and must not be 'fail'.
With no check given, the gate only reports and exits 0.

Exit codes: 0 gate passed, 1 gate failed, 2 bad input.
"""
import argparse
import json
import sys
from pathlib import Path

RANK = {"pass": 0, "mixed": 1, "fail": 2}


def load(path):
    try:
        data = json.loads(Path(path).read_text())
        crits = {}
        for group in data["groups"].values():
            for c in group["criteria"]:
                if c["status"] not in RANK:
                    raise ValueError(f"{c['id']}: bad status {c['status']!r}")
                crits[c["id"]] = c
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"gate: cannot use {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    if not crits:
        print(f"gate: {path} has no criteria", file=sys.stderr)
        sys.exit(2)
    return crits


def score(crits):
    total = sum(1 - RANK[c["status"]] / 2 for c in crits.values())
    return round(100 * total / len(crits))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--min-score", type=int)
    ap.add_argument("--baseline")
    ap.add_argument("--markdown", help="also write the summary as markdown (for a PR comment)")
    args = ap.parse_args()

    now = load(args.results)
    problems = []
    current = score(now)

    if args.min_score is not None and current < args.min_score:
        problems.append(f"overall score {current}% is below the minimum {args.min_score}%")

    base_score = None
    if args.baseline:
        if not Path(args.baseline).exists():
            print(f"gate: baseline {args.baseline} not found, skipping the regression check", file=sys.stderr)
        else:
            base = load(args.baseline)
            base_score = score(base)
            for cid, c in now.items():
                before = base.get(cid)
                if before is None:
                    if c["status"] == "fail":
                        problems.append(f"{cid} {c['title']}: new criterion fails - {c['message']}")
                elif RANK[c["status"]] > RANK[before["status"]]:
                    problems.append(f"{cid} {c['title']}: {before['status']} -> {c['status']} - {c['message']}")

    counts = {s: sum(c["status"] == s for c in now.values()) for s in RANK}
    delta = "" if base_score is None else f" (baseline {base_score}%, {current - base_score:+d})"
    lines = [f"Kedro quality check: {current}%{delta} - {counts['pass']} pass, {counts['mixed']} mixed, {counts['fail']} fail"]
    lines += [f"  FAIL GATE: {p}" for p in problems] or ["  Gate passed."]
    print("\n".join(lines))

    if args.markdown:
        md = [f"### Kedro quality check: {current}%{delta}",
              f"{counts['pass']} pass · {counts['mixed']} mixed · {counts['fail']} fail", ""]
        md += ([f"- ❌ {p}" for p in problems] if problems else ["✅ Gate passed."])
        Path(args.markdown).write_text("\n".join(md) + "\n")

    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
