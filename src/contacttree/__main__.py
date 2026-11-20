"""Command line: python -m contacttree build|check ROSTER.csv"""

from __future__ import annotations

import argparse
import csv
import sys

from .tree import build_tree, load_roster, render, stats, walk


def main(argv: list[str] | None = None) -> int:
    """Return 0 on success, 1 when the roster has problems, 2 for an unreadable file or bad option."""
    parser = argparse.ArgumentParser(prog="contacttree", description="Emergency call tree from a roster")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="print the call tree")
    b.add_argument("file")
    b.add_argument("--fanout", type=int, default=3, help="people each caller phones (default 3)")
    b.add_argument("--absent", default="", help="comma separated names who are away")
    b.add_argument("--format", choices=("tree", "csv"), default="tree")
    c = sub.add_parser("check", help="list roster problems")
    c.add_argument("file")
    args = parser.parse_args(argv)
    try:
        people, problems = load_roster(args.file)
    except FileNotFoundError:
        print(f"File not found: {args.file}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Cannot read {args.file}: {exc}", file=sys.stderr)
        return 2
    if args.command == "check":
        for p in problems:
            print(p)
        print(f"{len(people)} people, {len(problems)} problem(s)")
        return 1 if problems else 0
    absent = tuple(a for a in args.absent.split(",") if a.strip())
    unknown = [a for a in absent if a.strip().lower() not in {p.name.lower() for p in people}]
    if unknown:
        print("Unknown name(s) in --absent: " + ", ".join(unknown), file=sys.stderr)
        return 2
    try:
        root, away = build_tree(people, args.fanout, absent)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for p in problems:
        print(f"warning: {p}", file=sys.stderr)
    if args.format == "csv":
        w = csv.writer(sys.stdout, lineterminator="\n")
        w.writerow(["caller", "callee", "callee_role"])
        for caller, callee in walk(root):
            w.writerow([caller.name, callee.name, callee.role])
    else:
        print(render(root))
        print(stats(root, away))
    return 0


if __name__ == "__main__":
    sys.exit(main())
