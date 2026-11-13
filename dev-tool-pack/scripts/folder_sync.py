"""One-way folder sync: mirror source to destination."""
import os, sys, shutil, argparse, hashlib, filecmp

def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def sync(src, dst, dry_run=False, delete=False):
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if not os.path.isdir(src):
        print(f"Source not found: {src}")
        return
    os.makedirs(dst, exist_ok=True)

    copied = updated = skipped = deleted = 0

    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_root = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_root, exist_ok=True)
        for f in files:
            s = os.path.join(root, f)
            d = os.path.join(target_root, f)
            if not os.path.exists(d):
                if dry_run:
                    print(f"[NEW] {s} -> {d}")
                else:
                    shutil.copy2(s, d)
                    print(f"Copied: {s} -> {d}")
                copied += 1
            elif hash_file(s) != hash_file(d):
                if dry_run:
                    print(f"[UPDATE] {s} -> {d}")
                else:
                    shutil.copy2(s, d)
                    print(f"Updated: {s} -> {d}")
                updated += 1
            else:
                skipped += 1

    if delete:
        for root, dirs, files in os.walk(dst):
            rel = os.path.relpath(root, dst)
            src_root = src if rel == "." else os.path.join(src, rel)
            for f in files:
                d = os.path.join(root, f)
                s = os.path.join(src_root, f)
                if not os.path.exists(s):
                    if dry_run:
                        print(f"[DELETE] {d}")
                    else:
                        os.remove(d)
                        print(f"Deleted: {d}")
                    deleted += 1

    print(f"\nSync complete: {copied} copied, {updated} updated, {skipped} unchanged, {deleted} deleted.")

def main():
    ap = argparse.ArgumentParser(description="One-way folder sync (mirror source to destination)")
    ap.add_argument("source", help="Source folder")
    ap.add_argument("destination", help="Destination folder")
    ap.add_argument("--dry-run", action="store_true", help="Preview without changes")
    ap.add_argument("--delete", action="store_true", help="Delete files in dest not in source")
    args = ap.parse_args()
    sync(args.source, args.destination, args.dry_run, args.delete)

if __name__ == "__main__":
    main()
