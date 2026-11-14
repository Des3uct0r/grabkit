#!/usr/bin/env python3
"""find_big_files.py - list the largest files in a folder (and subfolders).

Read-only. Great for freeing disk space quickly.

Usage:
    python find_big_files.py C:/Users/me
    python find_big_files.py C:/ --top 20
    python find_big_files.py C:/Users/me --min 100  (only files >= 100 MB)
"""
import argparse, os, sys
from pathlib import Path

def human(n):
    for u in ("B","KB","MB","GB","TB"):
        if n < 1024: return ("%.1f %s" % (n, u)) if u != "B" else ("%d B" % n)
        n /= 1024.0
    return "%.1f PB" % n

def main():
    ap = argparse.ArgumentParser(description="Find the largest files.")
    ap.add_argument("folder", help="folder to scan")
    ap.add_argument("--top", type=int, default=25, help="how many to show (default 25)")
    ap.add_argument("--min", type=int, default=0, help="only files >= this many MB")
    args = ap.parse_args()
    root = Path(args.folder)
    if not root.is_dir():
        print("Error: folder not found: %s" % root); sys.exit(1)
    min_bytes = args.min * 1024 * 1024
    results = []
    for dirpath, dirs, files in os.walk(root):
        for f in files:
            p = Path(dirpath) / f
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            if sz >= min_bytes:
                results.append((sz, str(p)))
    results.sort(reverse=True)
    results = results[:args.top]
    if not results:
        print("No files found."); return
    print("Top %d largest files in %s:" % (len(results), root))
    print("%-12s  %s" % ("SIZE", "FILE"))
    for sz, p in results:
        print("%-12s  %s" % (human(sz), p))
    print("\nTotal scanned: %d files shown." % len(results))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled."); sys.exit(130)
