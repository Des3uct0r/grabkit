"""Watch a folder and auto-organize new files as they arrive."""
import os, sys, time, shutil, argparse

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xlsx", ".xls", ".csv", ".pptx", ".md"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Video": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".cpp", ".c", ".h", ".java", ".go", ".rs"},
}

def categorize(path):
    ext = os.path.splitext(path)[1].lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return "Other"

def organize_one(src, dest_root, dry_run=False):
    cat = categorize(src)
    target_dir = os.path.join(dest_root, cat)
    target = os.path.join(target_dir, os.path.basename(src))
    if dry_run:
        print(f"[DRY] {src} -> {target}")
        return
    os.makedirs(target_dir, exist_ok=True)
    if os.path.exists(target):
        base, ext = os.path.splitext(os.path.basename(src))
        i = 1
        while os.path.exists(os.path.join(target_dir, f"{base}_{i}{ext}")):
            i += 1
        target = os.path.join(target_dir, f"{base}_{i}{ext}")
    shutil.move(src, target)
    print(f"Moved: {src} -> {target}")

def main():
    ap = argparse.ArgumentParser(description="Watch a folder and auto-organize new files")
    ap.add_argument("watch_dir", help="Folder to watch")
    ap.add_argument("--dest", default=None, help="Destination root (default: watch_dir/organized)")
    ap.add_argument("--dry-run", action="store_true", help="Preview without moving")
    ap.add_argument("--interval", type=int, default=5, help="Check interval in seconds")
    args = ap.parse_args()

    watch_dir = os.path.abspath(args.watch_dir)
    dest = os.path.abspath(args.dest) if args.dest else os.path.join(watch_dir, "organized")
    seen = set(os.listdir(watch_dir)) if os.path.isdir(watch_dir) else set()

    print(f"Watching {watch_dir} (every {args.interval}s). Press Ctrl+C to stop.")
    try:
        while True:
            current = set(os.listdir(watch_dir))
            new_files = current - seen
            for f in new_files:
                full = os.path.join(watch_dir, f)
                if os.path.isfile(full):
                    organize_one(full, dest, args.dry_run)
            seen = current
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
