#!/usr/bin/env python3
"""GrabKit Desktop — point-and-click front end for the GrabKit scripts.

Pick a tool, pick a folder, press Run. No terminal, no flags to memorise.
Every destructive action asks for confirmation first; most tools preview
before they change anything.

Requires only Python 3.8+ with tkinter (included in the official installers).
"""

import json
import os
import queue
import subprocess
import sys
import threading
import traceback
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:  # pragma: no cover - only when tkinter is stripped
    sys.stderr.write(
        "tkinter is missing. Reinstall Python from python.org and keep the\n"
        "optional features ticked (tkinter / IDLE), then run this again.\n"
    )
    raise SystemExit(1)

APP_NAME = "GrabKit Desktop"
VERSION = "1.1"
HERE = Path(__file__).resolve().parent
SCRIPTS = HERE / "scripts"
IS_WINDOWS = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0


# --------------------------------------------------------------------------
# Tool registry. Each field becomes one widget in the form.
#   kind: folder | file | files | text | int | choice | bool
#   flag: CLI flag, or None for a positional argument
# --------------------------------------------------------------------------
TOOLS = [
    # ---------------- Files ----------------
    {
        "id": "organizer",
        "name": "Organise a folder",
        "group": "Files",
        "script": "file_organizer.py",
        "desc": "Sorts a messy folder (Downloads, Desktop, a client's dump) "
                "into Images / Documents / Audio / Video / Archives. "
                "Tick Preview first to see the plan without moving anything.",
        "fields": [
            {"key": "folder", "label": "Folder to organise", "kind": "folder",
             "flag": None, "required": True},
            {"key": "dry", "label": "Preview only — untick to actually move files",
             "kind": "bool", "flag": "--dry-run", "default": True},
            {"key": "by_date", "label": "Group by month instead of file type",
             "kind": "bool", "flag": "--by-date"},
        ],
    },
    {
        "id": "duplicates",
        "name": "Find duplicate files",
        "group": "Files",
        "script": "duplicate_finder.py",
        "desc": "Finds identical files by content (not by name) and shows how "
                "much space each group wastes. Listing is always safe.",
        "fields": [
            {"key": "folder", "label": "Folder to scan", "kind": "folder",
             "flag": None, "required": True},
            {"key": "delete", "label": "Delete duplicates (asks for confirmation)",
             "kind": "bool", "flag": "--delete", "danger": True},
            {"key": "report", "label": "Save report to file (optional)",
             "kind": "save", "flag": "--report"},
        ],
    },
    {
        "id": "size",
        "name": "What is eating my disk",
        "group": "Files",
        "script": "folder_size.py",
        "desc": "Shows the size of every subfolder, largest first, plus the "
                "10 biggest files. Great for a full drive.",
        "fields": [
            {"key": "path", "label": "Folder to measure", "kind": "folder",
             "flag": None, "required": True},
            {"key": "depth", "label": "Levels deep", "kind": "int", "flag": "--depth",
             "default": "1"},
            {"key": "files", "label": "Also list the 10 largest files",
             "kind": "bool", "flag": "--files"},
        ],
    },
    {
        "id": "backup",
        "name": "Back up a folder to ZIP",
        "group": "Files",
        "script": "backup_zip.py",
        "desc": "Creates one timestamped .zip of a folder. Point the output "
                "folder at a USB drive or cloud-synced folder for a real backup.",
        "fields": [
            {"key": "source", "label": "Folder to back up", "kind": "folder",
             "flag": None, "required": True},
            {"key": "out", "label": "Where to save the .zip (optional)",
             "kind": "folder", "flag": "-o"},
            {"key": "name", "label": "Name prefix (optional)", "kind": "text",
             "flag": "--name"},
            {"key": "exclude", "label": "Skip pattern, e.g. *.tmp (optional)",
             "kind": "text", "flag": "--exclude"},
        ],
    },
    {
        "id": "sync",
        "name": "Mirror one folder into another",
        "group": "Files",
        "script": "folder_sync.py",
        "desc": "One-way copy: destination ends up identical to source. "
                "Tick Preview to see what would be copied or deleted.",
        "fields": [
            {"key": "source", "label": "Source folder", "kind": "folder",
             "flag": None, "required": True},
            {"key": "dest", "label": "Destination folder", "kind": "folder",
             "flag": None, "required": True},
            {"key": "dry", "label": "Preview only (recommended)", "kind": "bool",
             "flag": "--dry-run", "default": True},
            {"key": "delete", "label": "Delete extras in destination",
             "kind": "bool", "flag": "--delete", "danger": True},
        ],
    },
    {
        "id": "rename",
        "name": "Bulk rename files",
        "group": "Files",
        "script": "bulk_rename.py",
        "desc": "Rename hundreds of files at once: add a prefix, number them "
                "001/002/003, lowercase them, or replace text in names. "
                "Dry-run by default — tick Apply to really rename.",
        "fields": [
            {"key": "folder", "label": "Folder", "kind": "folder", "flag": None,
             "required": True},
            {"key": "prefix", "label": "Add prefix", "kind": "text", "flag": "--prefix"},
            {"key": "suffix", "label": "Add suffix (before extension)",
             "kind": "text", "flag": "--suffix"},
            {"key": "number", "label": "Number them 001, 002, 003…",
             "kind": "bool", "flag": "--number"},
            {"key": "lower", "label": "Make lowercase", "kind": "bool", "flag": "--lower"},
            {"key": "replace", "label": "Replace in name (old → new)", "kind": "text",
             "flag": "--replace", "hint": "old=new", "special": "replace_pair"},
            {"key": "ext", "label": "Only these extensions, e.g. .jpg",
             "kind": "text", "flag": "--ext-filter"},
            {"key": "apply", "label": "Apply for real (unticked = preview)",
             "kind": "bool", "flag": "--apply", "danger": True},
        ],
    },
    {
        "id": "findreplace",
        "name": "Find & replace inside files",
        "group": "Files",
        "script": "find_replace.py",
        "desc": "Replace a word or link across many .txt/.md/.csv/.html/.py "
                "files in one go. Dry-run by default; .bak backups on request.",
        "fields": [
            {"key": "folder", "label": "Folder", "kind": "folder", "flag": None,
             "required": True},
            {"key": "find", "label": "Find this text", "kind": "text",
             "flag": "--find", "required": True},
            {"key": "replace", "label": "Replace with", "kind": "text",
             "flag": "--replace"},
            {"key": "ext", "label": "Extensions (space separated)",
             "kind": "text", "flag": "--ext", "default": ".txt .md .csv .html .py",
             "special": "split_words"},
            {"key": "apply", "label": "Apply for real (unticked = preview)",
             "kind": "bool", "flag": "--apply", "danger": True},
            {"key": "backup", "label": "Keep .bak copies (only when applying)",
             "kind": "bool", "flag": "--backup", "requires": ["apply"],
             "default": True},
        ],
    },
    {
        "id": "watch",
        "name": "Auto-organise new files (Pro)",
        "group": "Files",
        "script": "watch_folder.py",
        "desc": "Runs in the background and files away anything that lands in "
                "a folder. Leave this window open while it works.",
        "fields": [
            {"key": "dir", "label": "Folder to watch", "kind": "folder",
             "flag": None, "required": True},
            {"key": "dest", "label": "Move into (optional)", "kind": "folder",
             "flag": "--dest"},
            {"key": "interval", "label": "Check every N seconds", "kind": "int",
             "flag": "--interval", "default": "30"},
            {"key": "dry", "label": "Preview only", "kind": "bool",
             "flag": "--dry-run"},
        ],
    },
    # ---------------- Photos ----------------
    {
        "id": "resize",
        "name": "Resize / convert photos",
        "group": "Photos",
        "script": "image_resizer.py",
        "desc": "Shrink photos for email, web or a marketplace listing. "
                "Originals stay untouched; results go to a 'resized' subfolder.",
        "fields": [
            {"key": "folder", "label": "Folder of images", "kind": "folder",
             "flag": None, "required": True},
            {"key": "width", "label": "Max width in pixels", "kind": "int",
             "flag": "--max-width", "default": "1600"},
            {"key": "height", "label": "Max height (optional)", "kind": "int",
             "flag": "--max-height"},
            {"key": "format", "label": "Convert to", "kind": "choice",
             "flag": "--format", "choices": ["keep", "jpg", "png", "webp"],
             "default": "keep", "skip_value": "keep"},
            {"key": "quality", "label": "JPG/WEBP quality (1–100)", "kind": "int",
             "flag": "--quality", "default": "85"},
            {"key": "out", "label": "Output folder (optional)", "kind": "folder",
             "flag": "--out"},
        ],
    },
    {
        "id": "watermark",
        "name": "Watermark photos (Pro)",
        "group": "Photos",
        "script": "watermark_images.py",
        "desc": "Stamps your text onto every image — protect listings, "
                "portfolios and client previews.",
        "fields": [
            {"key": "folder", "label": "Folder of images", "kind": "folder",
             "flag": None, "required": True},
            {"key": "text", "label": "Watermark text", "kind": "text",
             "flag": "--text", "required": True, "default": "© your name"},
            {"key": "position", "label": "Position", "kind": "choice",
             "flag": "--position",
             "choices": ["bottom-right", "bottom-left", "top-right", "top-left", "center"],
             "default": "bottom-right"},
            {"key": "size", "label": "Font size", "kind": "int",
             "flag": "--font-size", "default": "36"},
            {"key": "opacity", "label": "Opacity 0–255", "kind": "int",
             "flag": "--opacity", "default": "140"},
            {"key": "out", "label": "Output folder (optional)", "kind": "folder",
             "flag": "--output"},
        ],
    },
    # ---------------- PDF ----------------
    {
        "id": "pdf_merge",
        "name": "Merge PDFs into one",
        "group": "PDF",
        "script": "pdf_toolkit.py",
        "sub": ["merge"],
        "desc": "Pick two or more PDFs in the order you want them and combine "
                "them into a single file.",
        "fields": [
            {"key": "files", "label": "PDF files (pick several)", "kind": "files",
             "flag": None, "required": True, "filetypes": [("PDF", "*.pdf")]},
            {"key": "out", "label": "Output file", "kind": "save_pdf",
             "flag": "-o", "default": "merged.pdf"},
            {"key": "force", "label": "Overwrite if it exists", "kind": "bool",
             "flag": "--force", "danger": True},
        ],
    },
    {
        "id": "pdf_split",
        "name": "Split a PDF into pages",
        "group": "PDF",
        "script": "pdf_toolkit.py",
        "sub": ["split"],
        "desc": "Writes one PDF per page into a new folder.",
        "fields": [
            {"key": "input", "label": "PDF to split", "kind": "file",
             "flag": None, "required": True, "filetypes": [("PDF", "*.pdf")]},
            {"key": "out", "label": "Output folder (optional)", "kind": "folder",
             "flag": "-o"},
        ],
    },
    {
        "id": "pdf_extract",
        "name": "Extract pages from a PDF",
        "group": "PDF",
        "script": "pdf_toolkit.py",
        "sub": ["extract"],
        "desc": "Keep only the pages you want, e.g. 1-3,7 or all.",
        "fields": [
            {"key": "input", "label": "PDF file", "kind": "file", "flag": None,
             "required": True, "filetypes": [("PDF", "*.pdf")]},
            {"key": "pages", "label": "Pages to keep", "kind": "text",
             "flag": "-p", "default": "1-3"},
            {"key": "out", "label": "Output file", "kind": "save_pdf", "flag": "-o",
             "default": "extracted.pdf"},
            {"key": "force", "label": "Overwrite if it exists", "kind": "bool",
             "flag": "--force", "danger": True},
        ],
    },
    {
        "id": "pdf_info",
        "name": "PDF info (pages, size)",
        "group": "PDF",
        "script": "pdf_toolkit.py",
        "sub": ["info"],
        "desc": "Shows page count, title and file size for a PDF.",
        "fields": [
            {"key": "input", "label": "PDF file", "kind": "file", "flag": None,
             "required": True, "filetypes": [("PDF", "*.pdf")]},
        ],
    },
    # ---------------- Data ----------------
    {
        "id": "csv_merge",
        "name": "Merge CSV files",
        "group": "Data",
        "script": "csv_toolkit.py",
        "sub": ["merge"],
        "desc": "Stacks every .csv in a folder that shares the same header "
                "into one file.",
        "fields": [
            {"key": "folder", "label": "Folder with CSV files", "kind": "folder",
             "flag": None, "required": True},
            {"key": "out", "label": "Output CSV", "kind": "save_csv", "flag": "-o",
             "required": True, "default": "combined.csv"},
        ],
    },
    {
        "id": "csv_split",
        "name": "Split a CSV into parts",
        "group": "Data",
        "script": "csv_toolkit.py",
        "sub": ["split"],
        "desc": "Cuts one CSV into N equal chunks, each with the header row.",
        "fields": [
            {"key": "file", "label": "CSV file", "kind": "file", "flag": None,
             "required": True, "filetypes": [("CSV", "*.csv")]},
            {"key": "chunks", "label": "How many parts", "kind": "int",
             "flag": "--chunks", "required": True, "default": "4"},
        ],
    },
    {
        "id": "csv_preview",
        "name": "Preview a CSV",
        "group": "Data",
        "script": "csv_toolkit.py",
        "sub": ["head"],
        "desc": "Shows the header and first rows so you can check a file fast.",
        "fields": [
            {"key": "file", "label": "CSV file", "kind": "file", "flag": None,
             "required": True, "filetypes": [("CSV", "*.csv")]},
            {"key": "rows", "label": "Rows to show", "kind": "int", "flag": "--rows",
             "default": "10"},
        ],
    },
    {
        "id": "csv_dedup",
        "name": "Remove duplicate rows (Pro)",
        "group": "Data",
        "script": "csv_advanced.py",
        "sub": ["dedup"],
        "desc": "Drops duplicate records by a key column — a clean mailing or "
                "product list in one click.",
        "fields": [
            {"key": "file", "label": "CSV file", "kind": "file", "flag": None,
             "required": True, "filetypes": [("CSV", "*.csv")]},
            {"key": "key", "label": "Key column (e.g. email)", "kind": "text",
             "flag": "--key", "required": True},
            {"key": "out", "label": "Output CSV (optional)", "kind": "save_csv",
             "flag": "--output"},
        ],
    },
    {
        "id": "csv_stats",
        "name": "Column statistics (Pro)",
        "group": "Data",
        "script": "csv_advanced.py",
        "sub": ["stats"],
        "desc": "Count, sum, average, min and max for one column.",
        "fields": [
            {"key": "file", "label": "CSV file", "kind": "file", "flag": None,
             "required": True, "filetypes": [("CSV", "*.csv")]},
            {"key": "col", "label": "Column name", "kind": "text",
             "flag": "--col", "required": True},
        ],
    },
    {
        "id": "csv_filter",
        "name": "Filter CSV rows (Pro)",
        "group": "Data",
        "script": "csv_advanced.py",
        "sub": ["filter"],
        "desc": "Keeps only rows where a column equals a value, and writes a "
                "new CSV.",
        "fields": [
            {"key": "file", "label": "CSV file", "kind": "file", "flag": None,
             "required": True, "filetypes": [("CSV", "*.csv")]},
            {"key": "col", "label": "Column name", "kind": "text",
             "flag": "--col", "required": True},
            {"key": "value", "label": "Value to keep", "kind": "text",
             "flag": "--value", "required": True},
            {"key": "out", "label": "Output CSV (optional)", "kind": "save_csv",
             "flag": "--output"},
        ],
    },
    # ---------------- Web ----------------
    {
        "id": "links",
        "name": "Extract links from a web page",
        "group": "Web",
        "script": "link_scraper.py",
        "desc": "Pulls every link from a page into a list or CSV. Handy for "
                "research, outreach lists and site audits.",
        "fields": [
            {"key": "url", "label": "Page URL", "kind": "text", "flag": None,
             "required": True, "default": "https://example.com"},
            {"key": "internal", "label": "Only links on the same site",
             "kind": "bool", "flag": "--internal-only"},
            {"key": "csv", "label": "Save to CSV (optional)", "kind": "save_csv",
             "flag": "--csv"},
            {"key": "status", "label": "Check that each link works", "kind": "bool",
             "flag": "--status"},
        ],
    },
    # ---------------- Security ----------------
    {
        "id": "password",
        "name": "Generate strong passwords",
        "group": "Security",
        "script": "password_tools.py",
        "sub": ["generate"],
        "desc": "Creates random passwords locally. Nothing is sent anywhere.",
        "fields": [
            {"key": "length", "label": "Length", "kind": "int", "flag": "--length",
             "default": "20"},
            {"key": "count", "label": "How many", "kind": "int", "flag": "--count",
             "default": "5"},
        ],
    },
]


# --------------------------------------------------------------------------
# Command building
# --------------------------------------------------------------------------
def build_command(tool, values):
    """Turn the form values into an argv list for the tool's script."""
    script = SCRIPTS / tool["script"]
    argv = [sys.executable, str(script)] + list(tool.get("sub", []))
    positionals = []
    flags = []
    for field in tool["fields"]:
        raw = values.get(field["key"])
        flag = field["flag"]
        kind = field["kind"]

        if kind == "bool":
            if raw and all(values.get(dep) for dep in field.get("requires", [])):
                flags.append(flag)
            continue

        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        if kind == "choice" and raw == field.get("skip_value"):
            continue

        special = field.get("special")
        if special == "replace_pair":
            if "=" not in raw:
                raise ValueError("Replace needs the form old=new, e.g. IMG=photo")
            old, new = raw.split("=", 1)
            flags += [flag, old, new]
        elif special == "split_words":
            flags.append(flag)
            flags += raw.split()
        elif kind == "files":
            positionals += [p for p in raw if p]
        elif flag is None:
            positionals.append(raw)
        else:
            flags += [flag, raw]
    # Positionals must come before the flags: argparse's nargs="+" options
    # (--ext .txt .md) would otherwise swallow the final positional argument.
    return argv + positionals + flags


def human_argv(argv):
    out = []
    for part in argv:
        text = str(part)
        out.append('"%s"' % text if " " in text else text)
    return " ".join(out)


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------
class GrabKitApp:
    def __init__(self, root):
        self.root = root
        self.process = None
        self.queue = queue.Queue()
        self.vars = {}
        self.current = None
        self._build()

    # ---------- layout ----------
    def _build(self):
        root = self.root
        root.title("%s %s" % (APP_NAME, VERSION))
        root.geometry("1020x680")
        root.minsize(860, 560)
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Muted.TLabel", foreground="#57606a")

        header = ttk.Frame(root, padding=(16, 12, 16, 6))
        header.pack(fill="x")
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Pick a tool → pick your folder → press Run. "
                 "Nothing is deleted without confirmation.",
            style="Muted.TLabel",
        ).pack(anchor="w")

        body = ttk.Frame(root, padding=(16, 6))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=310)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # --- tool list
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")
        bar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        bar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.column("#0", width=300, minwidth=260, stretch=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        groups = {}
        for tool in TOOLS:
            group = tool["group"]
            if group not in groups:
                groups[group] = self.tree.insert("", "end", text="  " + group,
                                                 open=True)
            self.tree.insert(groups[group], "end", iid=tool["id"],
                             text="   " + tool["name"])

        # --- right pane
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        self.title = ttk.Label(right, text="Choose a tool on the left",
                               style="Title.TLabel")
        self.title.grid(row=0, column=0, sticky="w")
        self.desc = ttk.Label(right, text="", style="Muted.TLabel",
                              wraplength=600, justify="left")
        self.desc.grid(row=1, column=0, sticky="w", pady=(2, 10))

        self.form = ttk.Frame(right)
        self.form.grid(row=2, column=0, sticky="ew")
        self.form.columnconfigure(1, weight=1)

        ttk.Separator(right).grid(row=2, column=0, sticky="sew", pady=(0, 6))

        console_frame = ttk.Frame(right)
        console_frame.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        self.console = tk.Text(console_frame, wrap="word", height=12,
                               font=("Consolas", 9), bg="#0d1117", fg="#d0d7de",
                               insertbackground="#d0d7de", relief="flat",
                               padx=8, pady=6)
        self.console.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(console_frame, orient="vertical",
                           command=self.console.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.console.configure(yscrollcommand=sb.set, state="disabled")

        actions = ttk.Frame(right)
        actions.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        self.run_btn = ttk.Button(actions, text="▶  Run", command=self._run,
                                  state="disabled")
        self.run_btn.pack(side="left")
        self.stop_btn = ttk.Button(actions, text="■  Stop", command=self._stop,
                                   state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))
        self.status = ttk.Label(actions, text="Ready", style="Muted.TLabel")
        self.status.pack(side="right")

        self.root.after(100, self._drain)
        first = TOOLS[0]
        self.tree.selection_set(first["id"])
        self.tree.focus(first["id"])

    # ---------- form ----------
    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        tool = next((t for t in TOOLS if t["id"] == sel[0]), None)
        if tool is None:
            return  # a group heading
        self.current = tool
        for child in self.form.winfo_children():
            child.destroy()
        self.vars = {}
        self.title.configure(text=tool["name"])
        self.desc.configure(text=tool["desc"])
        self.run_btn.configure(state="normal")

        row = 0
        for field in tool["fields"]:
            key = field["key"]
            kind = field["kind"]
            default = field.get("default", "")

            if kind == "bool":
                var = tk.BooleanVar(value=bool(field.get("default", False)))
                ttk.Checkbutton(self.form, text=field["label"], variable=var
                                ).grid(row=row, column=0, columnspan=3,
                                       sticky="w", pady=2)
                self.vars[key] = var
                row += 1
                continue

            ttk.Label(self.form, text=field["label"]).grid(
                row=row, column=0, sticky="w", padx=(0, 8), pady=3)

            if kind == "choice":
                var = tk.StringVar(value=str(default or field["choices"][0]))
                box = ttk.Combobox(self.form, textvariable=var, state="readonly",
                                   values=field["choices"], width=24)
                box.grid(row=row, column=1, sticky="w", pady=3)
            else:
                var = tk.StringVar(value=str(default))
                entry = ttk.Entry(self.form, textvariable=var)
                entry.grid(row=row, column=1, sticky="ew", pady=3)
                if field.get("hint"):
                    ttk.Label(self.form, text=field["hint"], style="Muted.TLabel"
                              ).grid(row=row, column=2, sticky="w", padx=(6, 0))

            if kind in ("folder", "file", "files", "save", "save_pdf", "save_csv"):
                ttk.Button(self.form, text="Browse…", width=9,
                           command=lambda f=field, v=var: self._browse(f, v)
                           ).grid(row=row, column=3, sticky="w", padx=(6, 0))
            self.vars[key] = var
            row += 1

        ttk.Label(self.form, text="").grid(row=row, column=0)

    def _browse(self, field, var):
        kind = field["kind"]
        types = field.get("filetypes")
        if kind == "folder":
            path = filedialog.askdirectory(title=field["label"])
        elif kind == "file":
            path = filedialog.askopenfilename(title=field["label"],
                                              filetypes=types or [("All files", "*.*")])
        elif kind == "files":
            path = filedialog.askopenfilenames(title=field["label"],
                                               filetypes=types or [("All files", "*.*")])
        else:
            suffix = ".csv" if kind == "save_csv" else (
                ".pdf" if kind == "save_pdf" else "")
            path = filedialog.asksaveasfilename(
                title=field["label"],
                defaultextension=suffix,
                filetypes=types or ([("CSV", "*.csv")] if kind == "save_csv"
                                    else [("PDF", "*.pdf")] if kind == "save_pdf"
                                    else [("All files", "*.*")]),
            )
        if path:
            if isinstance(path, tuple):
                var.set(";".join(path))
            else:
                var.set(path)

    # ---------- run ----------
    def _collect(self):
        values = {}
        for field in self.current["fields"]:
            var = self.vars.get(field["key"])
            if var is None:
                continue
            raw = var.get()
            if isinstance(raw, tuple):
                raw = list(raw)
            if field["kind"] == "files" and isinstance(raw, str):
                raw = [p for p in raw.split(";") if p]
            values[field["key"]] = raw
        return values

    def _run(self):
        if self.current is None or self.process is not None:
            return
        values = self._collect()

        for field in self.current["fields"]:
            if field.get("required"):
                raw = values.get(field["key"])
                empty = (raw is None or (isinstance(raw, str) and not raw.strip())
                         or (isinstance(raw, list) and not raw))
                if empty:
                    messagebox.showwarning(
                        "Missing information",
                        "Please fill in: %s" % field["label"])
                    return

        danger = any(f.get("danger") and values.get(f["key"])
                     for f in self.current["fields"])
        if danger:
            if not messagebox.askyesno(
                    "Are you sure?",
                    "This will really change files on disk.\n\n"
                    "Consider unticking the dangerous option and doing a "
                    "preview run first.\n\nContinue?"):
                return

        try:
            argv = build_command(self.current, values)
        except ValueError as exc:
            messagebox.showerror("Check the form", str(exc))
            return

        self._write("$ %s\n\n" % human_argv(argv[1:]))
        self.status.configure(text="Running…")
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        try:
            self.process = subprocess.Popen(
                argv,
                cwd=str(SCRIPTS),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError as exc:
            self.process = None
            self._write("Could not start Python: %s\n" % exc)
            self._finished()
            return

        threading.Thread(target=self._reader, args=(self.process,),
                         daemon=True).start()

    def _reader(self, process):
        try:
            for line in process.stdout:
                self.queue.put(line)
        except Exception:
            self.queue.put(traceback.format_exc())
        finally:
            process.wait()
            self.queue.put(("__done__", process.returncode))

    def _drain(self):
        try:
            while True:
                item = self.queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "__done__":
                    self._write("\n— finished (exit code %s) —\n" % item[1])
                    self.process = None
                    self._finished()
                else:
                    self._write(item)
        except queue.Empty:
            pass
        self.root.after(100, self._drain)

    def _finished(self):
        self.run_btn.configure(state="normal" if self.current else "disabled")
        self.stop_btn.configure(state="disabled")
        self.status.configure(text="Ready")

    def _stop(self):
        if self.process is not None:
            try:
                self.process.terminate()
            except OSError:
                pass
            self._write("\n[stopped]\n")

    def _write(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", text)
        self.console.see("end")
        self.console.configure(state="disabled")


def main():
    if not SCRIPTS.is_dir():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            APP_NAME,
            "The scripts folder is missing.\n\nUnzip the whole GrabKit "
            "archive first, then run Start GrabKit again.")
        return 1
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except tk.TclError:
        pass
    GrabKitApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
