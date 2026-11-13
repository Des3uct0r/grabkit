#!/usr/bin/env python3
"""pdf_toolkit.py - a small PDF toolbox: merge, split, extract pages, inspect.

Works with the free "pypdf" library. If it is missing you will get a friendly
one-line hint instead of a scary traceback:
    pip install pypdf

Usage examples:
    python pdf_toolkit.py merge a.pdf b.pdf c.pdf -o combined.pdf
    python pdf_toolkit.py split report.pdf -o pages
    python pdf_toolkit.py extract report.pdf -p 1-3,7 -o excerpt.pdf
    python pdf_toolkit.py info report.pdf

Exit codes: 0 = success, 1 = something went wrong, 2 = wrong command line usage.
"""

import argparse
import sys
from pathlib import Path

# Installed lazily so that "--help" and bad command lines still work
# even when pypdf is not installed.
PdfReader = PdfWriter = None


def _load_pypdf():
    """Import pypdf, or exit with a friendly install hint."""
    global PdfReader, PdfWriter
    if PdfReader is not None:
        return
    try:
        from pypdf import PdfReader as _R, PdfWriter as _W
    except ImportError:
        print("Error: the 'pypdf' library is not installed.")
        print("Install it with:  pip install pypdf")
        sys.exit(1)
    PdfReader, PdfWriter = _R, _W


def _human_size(num_bytes):
    """Turn a byte count into something readable, e.g. 1.4 MB."""
    size = float(num_bytes)
    for unit in ("bytes", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            if unit == "bytes":
                return "%d %s" % (int(size), unit)
            return "%.1f %s" % (size, unit)
        size /= 1024.0
    return "%.1f GB" % size


def _open_pdf(path_str):
    """Open a PDF file with clear error messages. Returns (reader, Path)."""
    path = Path(path_str)
    if not path.exists():
        print("Error: file not found: %s" % path)
        sys.exit(1)
    if not path.is_file():
        print("Error: not a file: %s" % path)
        sys.exit(1)
    try:
        reader = PdfReader(str(path))
        # Reading the page count also detects corrupt/locked files early.
        _ = len(reader.pages)
    except Exception as exc:
        print("Error: could not open '%s' as a PDF (%s)." % (path, exc))
        print("Hints: is it really a PDF? Is it password protected?")
        sys.exit(1)
    return reader, path


def parse_page_spec(spec, total_pages, what="page"):
    """Turn a human page spec like '1-3,5,all' into a sorted list of 0-based indexes.

    Page numbers are 1-based for the user, as in any PDF viewer.
    Raises SystemExit(2) with a clear message when the spec is invalid.
    """
    spec = (spec or "").strip()
    if not spec:
        print("Error: empty page selection (use e.g. -p 1-3,5 or -p all).")
        sys.exit(2)
    if spec.lower() == "all":
        return list(range(total_pages))

    chosen = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_txt, _, end_txt = part.partition("-")
            if not (start_txt.strip().isdigit() and end_txt.strip().isdigit()):
                print("Error: bad page range '%s'. Use numbers like 2-5." % part)
                sys.exit(2)
            start, end = int(start_txt), int(end_txt)
            if start < 1 or end < 1:
                print("Error: page numbers start at 1 (got '%s')." % part)
                sys.exit(2)
            if start > end:
                start, end = end, start  # be forgiving: 5-2 means 2-5
            if end > total_pages:
                print(
                    "Error: range '%s' goes past the last page "
                    "(this PDF has %d pages)." % (part, total_pages)
                )
                sys.exit(2)
            chosen.update(range(start - 1, end))
        elif part.isdigit():
            num = int(part)
            if num < 1:
                print("Error: page numbers start at 1 (got '%s')." % part)
                sys.exit(2)
            if num > total_pages:
                print(
                    "Error: %s %d does not exist (this PDF has %d pages)."
                    % (what, num, total_pages)
                )
                sys.exit(2)
            chosen.add(num - 1)
        else:
            print("Error: cannot understand page selection '%s'." % part)
            print("Examples: 1,3   1-5   2-4,7   all")
            sys.exit(2)

    if not chosen:
        print("Error: no pages selected (use e.g. -p 1-3,5 or -p all).")
        sys.exit(2)
    return sorted(chosen)


def cmd_merge(args):
    """Append several PDFs into one output file."""
    _load_pypdf()
    if len(args.files) < 2:
        print("Error: merge needs at least two PDFs, e.g.:")
        print("    python pdf_toolkit.py merge a.pdf b.pdf -o out.pdf")
        sys.exit(2)
    if not args.out:
        print("Error: please name the output file with -o, e.g. -o combined.pdf")
        sys.exit(2)
    out_path = Path(args.out)
    if out_path.exists() and not args.force:
        print("Error: output file already exists: %s" % out_path)
        print("Use --force to overwrite it.")
        sys.exit(1)
    if any(Path(f).resolve() == out_path.resolve() for f in args.files):
        print("Error: the output file is one of the inputs; pick a different -o name.")
        sys.exit(2)

    writer = PdfWriter()
    total_in = 0
    for file_str in args.files:
        reader, path = _open_pdf(file_str)
        for page in reader.pages:
            writer.add_page(page)
        total_in += len(reader.pages)
        print("Added %s (%d pages)" % (path, len(reader.pages)))
    try:
        with out_path.open("wb") as fh:
            writer.write(fh)
    except PermissionError:
        print("Error: cannot write to '%s' (is the file open in a PDF viewer?)" % out_path)
        sys.exit(1)
    print("Done: %d pages from %d files written to %s" % (total_in, len(args.files), out_path))


def cmd_split(args):
    """Write one PDF per page into an output folder."""
    _load_pypdf()
    reader, src = _open_pdf(args.input)
    n = len(reader.pages)
    out_dir = Path(args.out) if args.out else src.with_name(src.stem + "_pages")
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print("Error: cannot create folder '%s' (no permission?)" % out_dir)
        sys.exit(1)
    for index in parse_page_spec("all", n):
        writer = PdfWriter()
        writer.add_page(reader.pages[index])
        out_file = out_dir / ("%s_page_%03d.pdf" % (src.stem, index + 1))
        try:
            with out_file.open("wb") as fh:
                writer.write(fh)
        except PermissionError:
            print("Error: cannot write '%s' (is something locking it?)" % out_file)
            sys.exit(1)
        print("Wrote %s (page %d of %d)" % (out_file, index + 1, n))
    print("Done: %d single-page PDFs saved in %s" % (n, out_dir))


def cmd_extract(args):
    """Copy a selected page range into a new PDF."""
    _load_pypdf()
    if not args.out:
        print("Error: please name the output file with -o, e.g. -o excerpt.pdf")
        sys.exit(2)
    reader, src = _open_pdf(args.input)
    n = len(reader.pages)
    indexes = parse_page_spec(args.pages, n)
    out_path = Path(args.out)
    if out_path.exists() and not args.force:
        print("Error: output file already exists: %s" % out_path)
        print("Use --force to overwrite it.")
        sys.exit(1)
    writer = PdfWriter()
    for index in indexes:
        writer.add_page(reader.pages[index])
    try:
        with out_path.open("wb") as fh:
            writer.write(fh)
    except PermissionError:
        print("Error: cannot write '%s' (is the file open in a PDF viewer?)" % out_path)
        sys.exit(1)
    print("Done: %d page(s) [%s] from %s written to %s"
          % (len(indexes), args.pages, src, out_path))


def cmd_info(args):
    """Print a short summary: page count, title, file size."""
    _load_pypdf()
    reader, path = _open_pdf(args.input)
    meta = reader.metadata or {}
    title = str(meta.get("/Title")) if meta.get("/Title") else "(no title)"
    print("File      : %s" % path)
    print("Pages     : %d" % len(reader.pages))
    print("Title     : %s" % title)
    print("Size      : %s" % _human_size(path.stat().st_size))


def main():
    parser = argparse.ArgumentParser(
        prog="pdf_toolkit.py",
        description="Merge, split, extract pages from, and inspect PDF files.",
        epilog="Examples:\n"
               "  python pdf_toolkit.py merge a.pdf b.pdf -o out.pdf\n"
               "  python pdf_toolkit.py split report.pdf -o pages\n"
               "  python pdf_toolkit.py extract report.pdf -p 1-3,7 -o part.pdf\n"
               "  python pdf_toolkit.py info report.pdf",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    p = sub.add_parser("merge", help="combine several PDFs into one")
    p.add_argument("files", nargs="+", metavar="pdf", help="input PDF files, in order")
    p.add_argument("-o", "--out", help="output PDF file name")
    p.add_argument("--force", action="store_true", help="overwrite the output if it exists")
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("split", help="write one PDF per page into a folder")
    p.add_argument("input", help="the PDF to split")
    p.add_argument("-o", "--out", help="output folder (default: <pdf name>_pages)")
    p.set_defaults(func=cmd_split)

    p = sub.add_parser("extract", help="copy selected pages into a new PDF")
    p.add_argument("input", help="the PDF to extract pages from")
    p.add_argument("-p", "--pages", default="all",
                   help="pages to keep, e.g. 1-3,7 or 'all' (default: all)")
    p.add_argument("-o", "--out", help="output PDF file name")
    p.add_argument("--force", action="store_true", help="overwrite the output if it exists")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("info", help="show page count, title and file size")
    p.add_argument("input", help="the PDF to inspect")
    p.set_defaults(func=cmd_info)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
