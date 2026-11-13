#!/usr/bin/env python3
"""Create a timestamped zip backup of a folder. Nothing is deleted;
this script only creates a new zip file.

Usage examples:
  python backup_zip.py C:\\Users\\me\\Documents
  python backup_zip.py C:\\Users\\me\\Documents -o D:\\Backups
  python backup_zip.py C:\\Users\\me\\Documents --name work --exclude "*.tmp" --exclude "temp*"

The output zip is named like: work_2026-11-13_143005.zip
It never overwrites an existing backup: if that name is taken, a number
is added (work_2026-11-13_143005_1.zip).
"""

import argparse
import fnmatch
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Exit codes: 0 = success, 1 = error.
EXIT_OK = 0
EXIT_ERROR = 1


def is_excluded(rel_path, patterns):
    """True if a relative path matches any --exclude fnmatch pattern.

    Patterns match against the file's relative path and its name, so
    "*.tmp" catches files anywhere and "temp*" catches folders by name.
    """
    name = Path(rel_path).name
    for pattern in patterns:
        if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(name, pattern):
            return True
        # Also let a pattern like "temp*" match an intermediate folder.
        if any(fnmatch.fnmatch(part, pattern) for part in Path(rel_path).parts):
            return True
    return False


def next_free_path(directory, stem, suffix):
    """Return a zip path that does not exist yet, adding _1, _2, ... if needed."""
    candidate = directory / "{}{}".format(stem, suffix)
    counter = 1
    while candidate.exists():
        candidate = directory / "{}_{}{}".format(stem, counter, suffix)
        counter += 1
    return candidate


def main():
    parser = argparse.ArgumentParser(
        description="Create a timestamped zip backup of a folder."
    )
    parser.add_argument("source", help="Folder to back up, e.g. C:\\Users\\me\\Documents")
    parser.add_argument("-o", "--output-dir", default=None, metavar="DIR",
                        help="Where to put the zip (default: next to the source folder)")
    parser.add_argument("--name", default=None, metavar="PREFIX",
                        help="Name prefix for the zip (default: the source folder's name)")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                        help="Skip files/folders matching this pattern (fnmatch), "
                             "e.g. --exclude \"*.tmp\". Can be given several times.")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print("Folder not found: {}".format(source))
        return EXIT_ERROR
    if not source.is_dir():
        print("Not a folder: {}".format(source))
        return EXIT_ERROR

    # Decide where the zip goes.
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_dir():
            try:
                output_dir.mkdir(parents=True)
                print("Created output folder: {}".format(output_dir))
            except OSError as exc:
                print("Could not create output folder {}: {}".format(output_dir, exc))
                return EXIT_ERROR
    else:
        # Default: alongside the source folder (its parent directory).
        output_dir = source.parent

    prefix = args.name if args.name else source.name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    zip_path = next_free_path(output_dir, "{}_{}".format(prefix, timestamp), ".zip")

    if args.exclude:
        print("Excluding patterns: {}".format(", ".join(args.exclude)))
    print("Backing up {} -> {}".format(source, zip_path))
    print("Scanning and compressing ...")

    # Collect all files first (so we can report a clean summary).
    to_zip = []  # (absolute_path, arcname)
    excluded = 0
    for dirpath, dirs, names in os.walk(source):
        dirs[:] = [d for d in dirs if not Path(dirpath, d).is_symlink()]
        for name in names:
            path = Path(dirpath) / name
            rel = path.relative_to(source.parent)
            if is_excluded(str(path.relative_to(source)), args.exclude):
                excluded += 1
                continue
            to_zip.append((path, str(rel)))

    if not to_zip:
        print("Nothing to back up - the source folder is empty "
              "(or everything was excluded). No zip was created.")
        return EXIT_ERROR

    # Write the zip. ZIP_DEFLATED compresses; if zlib is missing this
    # silently falls back to ZIP_STORED, which still works.
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, arcname in to_zip:
                try:
                    zf.write(str(path), arcname)
                except OSError as exc:
                    print("  Skipped (could not read): {} - {}".format(path, exc))
    except OSError as exc:
        print("Could not create the zip file: {}".format(exc))
        return EXIT_ERROR

    # Success summary.
    size = zip_path.stat().st_size
    print("\nBackup complete.")
    print("  Zip file: {}".format(zip_path))
    print("  Files backed up: {}".format(len(to_zip)))
    if excluded:
        print("  Files excluded:  {}".format(excluded))
    print("  Zip size:        {:.1f} MB".format(size / (1024 * 1024)) if size >= 1024 * 1024
          else "  Zip size:        {:.1f} KB".format(size / 1024))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
