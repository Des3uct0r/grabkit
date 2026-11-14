#!/usr/bin/env python3
"""find_replace.py - Find and replace text across many text files in a folder tree.

By default this is a DRY RUN: it only reports how many matches each file has.
Files are only modified when you pass --apply.

Usage examples:
    python find_replace.py C:\\notes --find acme --replace AcmeCorp
    python find_replace.py C:\\site --find "TODO: " --replace "DONE: " --apply
    python find_replace.py C:\\notes --find 2023 --replace 2024 --apply --backup
    python find_replace.py C:\\code --find oldFunc --replace newFunc --ext .py .js

How it works:
    - Walks the folder tree (subfolders included), skipping hidden folders,
      common junk folders (like __pycache__ and node_modules) and the
      backup files this script creates.
    - Only reads files whose extension is in the --ext list, and only files
      that decode as text (UTF-8 first, then a permissive fallback).
    - --backup creates a copy next to each changed file: notes.txt.bak
"""

import argparse
import shutil
import sys
from pathlib import Path

# Extensions that are treated as editable text by default.
DEFAULT_EXTS = [".txt", ".md", ".csv", ".html", ".py"]

# Folder names that are never searched (temp/dependency/build folders).
SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".hg", ".svn",
             ".venv", "venv", ".tox", "dist", "build"}


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Find and replace text across text files (dry-run by default).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("folder", help="Folder to search (subfolders are included).")
    parser.add_argument("--find", required=True, metavar="TEXT",
                        help="Text to search for.")
    parser.add_argument("--replace", default="", metavar="TEXT",
                        help="Replacement text (default: empty string, i.e. delete matches).")
    parser.add_argument("--ext", nargs="+", default=DEFAULT_EXTS, metavar="EXT",
                        help="File extensions to process, e.g. --ext .txt .md")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show match counts only (this is the default).")
    parser.add_argument("--apply", action="store_true",
                        help="Write the changes to the files.")
    parser.add_argument("--backup", action="store_true",
                        help="With --apply: save a .bak copy of each file before writing.")
    return parser


def normalize_extensions(ext_list):
    """Return extensions as lowercase dotted strings, e.g. '.txt'.

    Accepts both "--ext .txt .md" (separate arguments) and
    "--ext .txt,.md" (one comma-separated argument).
    """
    raw = []
    for item in ext_list:
        raw.extend(part for part in item.split(",") if part.strip())
    result = []
    for ext in raw:
        ext = ext.lower().strip()
        if not ext.startswith("."):
            ext = "." + ext
        result.append(ext)
    return result


def read_text_safe(path):
    """Read a file as text, trying UTF-8 then a permissive fallback.

    Returns (text, encoding) or (None, None) if the file is not readable text
    (e.g. it contains NUL bytes, so it is probably binary).
    """
    raw = path.read_bytes()
    if b"\x00" in raw:
        return None, None  # binary file, do not touch
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return None, None


def iter_candidate_files(folder, exts):
    """Yield files in the tree whose extension matches, skipping junk folders."""
    for path in folder.rglob("*"):
        # Skip hidden folders and known junk folders entirely.
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS or part.startswith(".") for part in path.parts[len(folder.parts):]):
            continue
        if path.suffix.lower() not in exts:
            continue
        if not path.is_file():
            continue
        # Never touch our own backup files.
        if path.name.endswith(".bak"):
            continue
        yield path


def main():
    args = build_arg_parser().parse_args()

    if args.backup and not args.apply:
        print("NOTE: --backup only takes effect together with --apply.")
        if args.dry_run:
            print("NOTE: --dry-run and the default dry run only report matches.")

    folder = Path(args.folder)
    if not folder.is_dir():
        print("ERROR: '%s' is not a folder (check the spelling and location)." % folder)
        sys.exit(2)

    exts = normalize_extensions(args.ext)

    mode = "APPLY (files will be modified)" if args.apply else "DRY RUN (nothing written)"
    print("Folder: %s" % folder)
    print("Find:    %r" % args.find)
    print("Replace: %r" % args.replace)
    print("Extensions: %s" % ", ".join(exts))
    print("Mode: %s" % mode)
    print("-" * 70)

    files_scanned = 0
    files_with_matches = 0
    total_matches = 0
    files_changed = 0
    files_errored = 0

    for path in iter_candidate_files(folder, exts):
        files_scanned += 1
        text, encoding = read_text_safe(path)
        if text is None:
            print("SKIP (binary or unreadable): %s" % path)
            files_errored += 1
            continue

        count = text.count(args.find)
        if count == 0:
            continue

        files_with_matches += 1
        total_matches += count
        print("%-8s %3d match(es)  %s" % ("FOUND", count, path))

        if not args.apply:
            continue

        new_text = text.replace(args.find, args.replace)
        try:
            if args.backup:
                bak_path = path.with_name(path.name + ".bak")
                shutil.copy2(path, bak_path)  # copy2 keeps timestamps
            with open(path, "w", encoding=encoding, newline="") as handle:
                handle.write(new_text)
            files_changed += 1
            if args.backup:
                print("         backup: %s" % bak_path)
        except OSError as exc:
            files_errored += 1
            print("  ERROR writing '%s': %s" % (path, exc))

    print("-" * 70)
    print("Scanned: %d file(s) | with matches: %d | total matches: %d"
          % (files_scanned, files_with_matches, total_matches))
    if args.apply:
        print("Changed: %d file(s) | skipped/failed: %d" % (files_changed, files_errored))
        if args.backup:
            print("Backups were saved as *.bak next to each changed file.")
    else:
        print("Dry run finished. Nothing was written.")
        print("Happy with the counts? Run the same command again with --apply.")
        print("Tip: add --backup to keep a .bak copy of every changed file.")
    if total_matches == 0:
        print("Nothing matched — check the search text or the extensions.")
        sys.exit(1)  # nothing found, matching greps' convention


if __name__ == "__main__":
    main()
