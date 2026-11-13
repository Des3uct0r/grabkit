# GrabKit — 12 Ready-to-Run Automation Scripts

Small jobs your computer makes you do by hand — sorted in seconds with one command each.
No coding, no installs, no accounts. Every tool previews what it will do before it does it.

## Setup (2 minutes, once)

1. Install Python 3.8+ from https://python.org (Windows: tick **"Add python.exe to PATH"** during install)
2. Optional — enables the PDF and image tools:
   ```
   pip install -r requirements.txt
   ```
   (Everything else runs on plain Python alone.)

**How to run a tool:** open a terminal in the `scripts` folder and type `python tool_name.py` + your options. Or right-click in your target folder while holding Shift → "Open in Terminal" and use full paths as shown below.

---

## The 12 tools

### 1. File Organizer — clean up a messy folder
Sorts files into `Images / Documents / Audio / Video / Archives / Code / Other` subfolders.
```
python file_organizer.py C:\Users\you\Downloads --dry-run     (preview the plan — moves nothing)
python file_organizer.py C:\Users\you\Downloads               (do it)
python file_organizer.py C:\photos --by-date                  (organize into 2026-11 style folders)
```
Real preview output:
```
FILE                    MOVE TO
dup1.txt                Documents
photo.jpg               Images
song.mp3                Audio
```

### 2. Duplicate Finder — find (and optionally delete) copies
Finds duplicates **by content**, not by name — works across subfolders.
```
python duplicate_finder.py C:\projects              (list duplicate groups)
python duplicate_finder.py C:\projects --report dup.txt
python duplicate_finder.py C:\projects --delete     (asks you to type yes)
```
```
Group 1 - 2 copies of 23 B
  ...\dup1.txt [KEEP]
  ...\sub\dup2.txt [COPY]
```

### 3. Folder Size — what's eating your disk
```
python folder_size.py C:\            (first-level folders, largest first)
python folder_size.py C:\ --files    (also shows the 10 biggest files)
```

### 4. Backup Zip — one-command folder backup
Creates a timestamped zip that never overwrites an earlier backup.
```
python backup_zip.py C:\my-project
python backup_zip.py C:\my-project -o D:\backups --name project --exclude "*.mp4" "*.tmp"
```
```
Backup complete.
  Zip file: D:\backups\project_2026-11-13_154015.zip
  Files backed up: 6    Zip size: 0.8 KB
```

### 5. Bulk Rename — fix 500 filenames at once
```
python bulk_rename.py C:\photos --number --ext-filter ".jpg"    (dry-run preview first)
python bulk_rename.py C:\photos --number --apply
python bulk_rename.py C:\photos --prefix "2026-" --lower --apply
```
```
Vacation Photo 1.JPG  ->  001.JPG
Vacation Photo 2.JPG  ->  002.JPG
```

### 6. Find & Replace — edit hundreds of files in one shot
```
python find_replace.py C:\notes --find acme --replace AcmeCorp                  (count only)
python find_replace.py C:\notes --find acme --replace AcmeCorp --apply --backup  (with .bak copies)
python find_replace.py C:\notes --find TODO --replace DONE --ext ".txt,.md"
```

### 7. CSV Toolkit — merge, split, count, preview
```
python csv_toolkit.py merge C:\reports -o combined.csv    (merges all CSVs in the folder)
python csv_toolkit.py split combined.csv --chunks 4
python csv_toolkit.py count combined.csv
python csv_toolkit.py head combined.csv --rows 3
```
Quoted fields like `"Smith, John"` are handled correctly.

### 8. Text Diff — compare two text files line by line
```
python text_diff.py old.txt new.txt
python text_diff.py old.txt new.txt --context 5
```
```
@@ File A lines 1-1 / File B lines 1-1 (changed)
  - A  1 | alpha beta
  + B  1 | alpha gamma
Summary: 1 added, 1 removed, 0 unchanged line(s).
```

### 9. PDF Toolkit — merge, split, extract, inspect
```
python pdf_toolkit.py merge a.pdf b.pdf c.pdf -o combined.pdf
python pdf_toolkit.py split combined.pdf -o pages          (one PDF per page)
python pdf_toolkit.py extract combined.pdf -p 1-3 -o part.pdf
python pdf_toolkit.py info combined.pdf
```

### 10. Image Resizer — bulk resize/convert photos
Originals are never modified; results go into a `resized` subfolder.
```
python image_resizer.py C:\photos --max-width 1200                 (keep aspect ratio)
python image_resizer.py C:\photos --max-width 800 --format webp --quality 85
```
```
Resized ...\p1.jpg -> 600x400
Summary: 3 processed, 4 skipped, 0 failed.
```

### 11. Link Scraper — pull every link from a web page
```
python link_scraper.py https://example.org
python link_scraper.py https://example.org --internal-only
python link_scraper.py https://example.org --csv links.csv
python link_scraper.py https://example.org --status       (check each link's status code)
```

### 12. Password Tools — generate & check passwords
```
python password_tools.py generate --length 16 --count 3
python password_tools.py generate --length 12 --no-symbols
python password_tools.py check        (type a password invisibly; get a strength report)
```

---

## Safety first
- Every destructive action needs an extra step: `--dry-run`/`--apply`, or typing `yes`
- `--backup` creates `.bak` copies before touching your files
- The tools never delete things silently and never touch files outside the folder you give them

## Troubleshooting
| Problem | Fix |
|---|---|
| `'python' is not recognized` | Python isn't installed or PATH wasn't ticked — reinstall python.org's installer |
| PDF or image tool says "pip install ..." | Run `pip install -r requirements.txt` |
| Non-English characters look wrong | Files should be saved as UTF-8 |
| Ran something by mistake | Most tools have no destructive default; where you used `--apply` without `--backup`, restore from a GrabKit backup zip next time |

## License
MIT-style permissive license (see LICENSE) — use it at home and at work, no attribution required.
