#!/usr/bin/env python3
"""text_diff.py - Compare two text files line by line and show a clean diff.

Prints a unified-style diff with line numbers for every changed region,
followed by a short summary (added / removed / unchanged lines).

Usage examples:
    python text_diff.py draft_v1.txt draft_v2.txt
    python text_diff.py config_old.ini config_new.ini --context 3
    python text_diff.py a.csv b.csv --context 0

Reading the output:
    lines starting with "+" exist only in fileB (added)
    lines starting with "-" exist only in fileA (removed)
    lines starting with " " are unchanged (context)
"""

import argparse
import difflib
import sys
from pathlib import Path


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Compare two text files and print a numbered unified diff.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("fileA", help="First (original) file.")
    parser.add_argument("fileB", help="Second (new) file.")
    parser.add_argument("--context", "-c", type=int, default=2, metavar="N",
                        help="Unchanged lines to show around each change (default: 2).")
    return parser


def read_lines(path):
    """Read a file as text and return its lines without line endings."""
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
            return handle.read().splitlines()
    except OSError as exc:
        print("ERROR: cannot read '%s': %s" % (path, exc))
        sys.exit(2)


def main():
    args = build_arg_parser().parse_args()

    file_a = Path(args.fileA)
    file_b = Path(args.fileB)

    if not file_a.is_file():
        print("ERROR: '%s' is not a file (check the spelling and location)." % file_a)
        sys.exit(2)
    if not file_b.is_file():
        print("ERROR: '%s' is not a file (check the spelling and location)." % file_b)
        sys.exit(2)
    if args.context < 0:
        print("ERROR: --context must be 0 or more.")
        sys.exit(2)

    lines_a = read_lines(file_a)
    lines_b = read_lines(file_b)

    print("File A: %s  (%d lines)" % (file_a, len(lines_a)))
    print("File B: %s  (%d lines)" % (file_b, len(lines_b)))
    print("=" * 70)

    matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)
    added = removed = unchanged = 0
    printed_anything = False

    opcodes = matcher.get_opcodes()
    for idx, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        if tag == "equal":
            unchanged += i2 - i1
            continue

        printed_anything = True

        if tag == "replace":
            print("@@ File A lines %d-%d / File B lines %d-%d (changed)"
                  % (i1 + 1, i2, j1 + 1, j2))
            for k in range(i1, i2):
                removed += 1
                print("  - A %5d | %s" % (k + 1, lines_a[k]))
            for k in range(j1, j2):
                added += 1
                print("  + B %5d | %s" % (k + 1, lines_b[k]))

        elif tag == "delete":
            print("@@ File A lines %d-%d removed" % (i1 + 1, i2))
            for k in range(i1, i2):
                removed += 1
                print("  - A %5d | %s" % (k + 1, lines_a[k]))

        elif tag == "insert":
            print("@@ File B lines %d-%d added" % (j1 + 1, j2))
            for k in range(j1, j2):
                added += 1
                print("  + B %5d | %s" % (k + 1, lines_b[k]))

        # Print a few unchanged lines after the change as context, but stop
        # early if the next change starts right here (it will print its own).
        ctx_end = min(i2 + args.context, len(lines_a))
        next_change_start = None
        if idx + 1 < len(opcodes):
            next_change_start = opcodes[idx + 1][1]
        if next_change_start is not None:
            ctx_end = min(ctx_end, next_change_start)
        if ctx_end > i2:
            for k in range(i2, ctx_end):
                print("    A %5d | %s" % (k + 1, lines_a[k]))

    if not printed_anything:
        print("The two files are identical.")
        sys.exit(0)

    print("=" * 70)
    print("Summary: %d added, %d removed, %d unchanged line(s)."
          % (added, removed, unchanged))
    sys.exit(1)  # files differ: conventional exit code for diff tools


if __name__ == "__main__":
    main()
