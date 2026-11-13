#!/usr/bin/env python3
"""csv_toolkit.py - Everyday CSV chores in one script: merge, split, head, count.

All commands use Python's csv module, so quoted fields, commas inside
quotes and multi-line cells are handled correctly.

Usage examples:
    python csv_toolkit.py merge C:\\invoices --output combined.csv
    python csv_toolkit.py split C:\\big.csv --chunks 5
    python csv_toolkit.py head C:\\big.csv --rows 10
    python csv_toolkit.py count C:\\big.csv
"""

import argparse
import csv
import sys
from pathlib import Path


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Merge, split, preview and count CSV files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # merge
    p_merge = sub.add_parser("merge",
                             help="Concatenate many CSVs with the same header into one.")
    p_merge.add_argument("folder", help="Folder containing the .csv files to merge.")
    p_merge.add_argument("--output", "-o", required=True, metavar="FILE",
                         help="Output CSV file (e.g. combined.csv).")
    p_merge.add_argument("--ext-filter", default=None, metavar="EXT",
                         help="Only merge files with this extension (default: .csv).")

    # split
    p_split = sub.add_parser("split",
                             help="Split one CSV into N row-chunks (each keeps the header).")
    p_split.add_argument("file", help="The CSV file to split.")
    p_split.add_argument("--chunks", type=check_chunks, required=True, metavar="N",
                         help="Number of chunks to create (each gets a fair share of rows).")
    p_split.add_argument("--prefix", default=None, metavar="NAME",
                         help="Output name prefix (default: <input name>_partNN).")

    # head
    p_head = sub.add_parser("head", help="Print the header and the first N data rows.")
    p_head.add_argument("file", help="The CSV file to preview.")
    p_head.add_argument("--rows", type=check_positive, default=5, metavar="N",
                        help="How many data rows to show (default: 5).")

    # count
    p_count = sub.add_parser("count", help="Count the data rows in a CSV.")
    p_count.add_argument("file", help="The CSV file to count rows in.")

    return parser


def open_reader(path):
    """Open a CSV file for reading with csv-safe settings."""
    try:
        handle = open(path, "r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        print("ERROR: cannot open '%s': %s" % (path, exc))
        sys.exit(2)
    return handle, csv.reader(handle)


def check_chunks(value):
    """Validate --chunks for the split command (must be 1 or more)."""
    try:
        value = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("--chunks must be a whole number")
    if value < 1:
        raise argparse.ArgumentTypeError("--chunks must be at least 1")
    return value


def check_positive(value):
    """Validate --rows for the head command (0 or more)."""
    try:
        value = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("--rows must be a whole number")
    if value < 0:
        raise argparse.ArgumentTypeError("--rows must be 0 or more")
    return value


def cmd_merge(args):
    folder = Path(args.folder)
    if not folder.is_dir():
        print("ERROR: '%s' is not a folder (check the spelling and location)." % folder)
        sys.exit(2)

    ext = (args.ext_filter or ".csv").lower()
    if not ext.startswith("."):
        ext = "." + ext
    inputs = [p for p in sorted(folder.iterdir())
              if p.is_file() and p.suffix.lower() == ext]
    output = Path(args.output)

    # Never read from our own output file if it sits in the same folder.
    inputs = [p for p in inputs if p.resolve() != output.resolve()]
    if not inputs:
        print("No .csv files found in '%s'. Nothing to merge." % folder)
        sys.exit(1)

    header = None
    total_rows = 0
    used_files = 0
    skipped = []

    out_handle = None
    try:
        out_handle = open(output, "w", encoding="utf-8", newline="")
        writer = csv.writer(out_handle)

        for path in inputs:
            try:
                handle, reader = open_reader(path)
            except UnicodeDecodeError as exc:
                skipped.append((path.name, "not readable as UTF-8 text (%s)" % exc.reason))
                continue
            try:
                try:
                    file_header = next(reader)
                except UnicodeDecodeError as exc:
                    skipped.append((path.name,
                                    "not readable as UTF-8 text (%s)" % exc.reason))
                    continue
                except StopIteration:
                    skipped.append((path.name, "empty file"))
                    continue

                if header is None:
                    header = file_header
                    writer.writerow(header)
                elif file_header != header:
                    skipped.append((path.name, "different header: %s" % file_header))
                    continue

                rows = 0
                try:
                    for row in reader:
                        writer.writerow(row)
                        rows += 1
                except UnicodeDecodeError as exc:
                    skipped.append((path.name,
                                    "bad characters after %d row(s) (%s)"
                                    % (rows, exc.reason)))
                    continue
                total_rows += rows
                used_files += 1
                print("merged %-30s %6d row(s)" % (path.name, rows))
            finally:
                handle.close()
    except OSError as exc:
        print("ERROR while writing '%s': %s" % (output, exc))
        sys.exit(2)
    finally:
        if out_handle:
            out_handle.close()

    for name, reason in skipped:
        print("skipped %-30s %s" % (name, reason))

    print("-" * 50)
    print("Merged %d file(s) into '%s' (%d data rows, 1 header row)."
          % (used_files, output, total_rows))


def cmd_split(args):
    src = Path(args.file)
    if not src.is_file():
        print("ERROR: '%s' is not a file (check the spelling and location)." % src)
        sys.exit(2)

    chunks = args.chunks
    prefix = args.prefix or (src.stem + "_part")

    try:
        with open(src, "r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
    except UnicodeDecodeError:
        print("ERROR: '%s' contains characters that are not valid UTF-8 text."
              % src)
        print("The file may be saved in another encoding (for example UTF-16).")
        print("Re-save it as UTF-8 or CSV in your spreadsheet program and retry.")
        sys.exit(2)

    if len(rows) < 1:
        print("ERROR: '%s' is empty; nothing to split." % src)
        sys.exit(1)

    header, data = rows[0], rows[1:]
    if not data:
        print("ERROR: '%s' has a header but no data rows; nothing to split." % src)
        sys.exit(1)

    # Share data rows as evenly as possible across the chunks.
    base, extra = divmod(len(data), chunks)
    sizes = [base + (1 if i < extra else 0) for i in range(chunks)]

    start = 0
    width = len(str(chunks))  # pad part numbers: part1 ... part10
    out_dir = src.parent  # parts land next to the source file, not in the terminal's folder
    for i, size in enumerate(sizes, start=1):
        part_rows = data[start:start + size]
        start += size
        out_name = out_dir / ("%s%s.csv" % (prefix, str(i).zfill(width)))
        with open(out_name, "w", encoding="utf-8", newline="") as out_handle:
            writer = csv.writer(out_handle)
            writer.writerow(header)
            writer.writerows(part_rows)
        print("wrote %-40s %6d row(s)" % (out_name, len(part_rows)))

    print("-" * 50)
    print("Split %d data row(s) from '%s' into %d chunk(s)."
          % (len(data), src, chunks))


def cmd_head(args):
    src = Path(args.file)
    if not src.is_file():
        print("ERROR: '%s' is not a file (check the spelling and location)." % src)
        sys.exit(2)

    handle, reader = open_reader(src)
    try:
        try:
            header = next(reader)
        except UnicodeDecodeError:
            print("ERROR: '%s' contains characters that are not valid UTF-8 text." % src)
            print("Re-save the file as UTF-8 in your editor and retry.")
            sys.exit(2)
        except StopIteration:
            print("'%s' is empty." % src)
            sys.exit(1)
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) >= args.rows:
                break
    finally:
        handle.close()

    print("File: %s" % src)
    print("Header: %s" % " | ".join(header))
    print("-" * 50)
    for row in rows:
        print(" | ".join(row))
    if not rows:
        print("(no data rows in this file)")
    else:
        print("-" * 50)
        print("Showing %d of the first row(s)." % len(rows))


def cmd_count(args):
    src = Path(args.file)
    if not src.is_file():
        print("ERROR: '%s' is not a file (check the spelling and location)." % src)
        sys.exit(2)

    handle, reader = open_reader(src)
    try:
        try:
            next(reader)  # header row
            has_header = True
        except UnicodeDecodeError:
            print("ERROR: '%s' contains characters that are not valid UTF-8 text." % src)
            print("Re-save the file as UTF-8 in your editor and retry.")
            sys.exit(2)
        except StopIteration:
            has_header = False
        rows = sum(1 for _ in reader)
    finally:
        handle.close()

    print("File: %s" % src)
    if has_header:
        print("Data rows (without header): %d" % rows)
    else:
        print("Data rows: %d" % rows)


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.command == "merge":
        cmd_merge(args)
    elif args.command == "split":
        # Validate --chunks type errors nicely.
        cmd_split(args)
    elif args.command == "head":
        cmd_head(args)
    elif args.command == "count":
        cmd_count(args)


if __name__ == "__main__":
    main()
