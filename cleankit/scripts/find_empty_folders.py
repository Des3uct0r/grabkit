#!/usr/bin/env python3
"""find_empty_folders.py - find empty folders (and folders with only empty subfolders).

Read-only. Safe to run; nothing is deleted.

Usage:
    python find_empty_folders.py C:/Users/me
    python find_empty_folders.py C:/Users/me --delete   (asks for confirmation)
"""
import argparse, os, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description="Find empty folders.")
    ap.add_argument("folder", help="folder to scan")
    ap.add_argument("--delete", action="store_true", help="delete them (asks first)")
    args = ap.parse_args()
    root = Path(args.folder)
    if not root.is_dir():
        print("Error: folder not found: %s" % root); sys.exit(1)
    empty = []
    for dirpath, dirs, files in os.walk(root, topdown=False):
        p = Path(dirpath)
        if p == root:
            continue
        # a folder is "empty" if it has no files and all subdirs are empty
        try:
            if not any(p.iterdir()):
                empty.append(p)
        except OSError:
            pass
    if not empty:
        print("No empty folders found."); return
    print("Empty folders in %s:" % root)
    for p in empty:
        print("  %s" % p)
    print("\nTotal: %d" % len(empty))
    if args.delete:
        ans = input("Delete all %d? Type yes: " % len(empty))
        if ans.strip().lower() == "yes":
            for p in empty:
                try:
                    p.rmdir(); print("Deleted %s" % p)
                except Exception as e:
                    print("Could not delete %s: %s" % (p, e))
        else:
            print("Cancelled.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled."); sys.exit(130)
