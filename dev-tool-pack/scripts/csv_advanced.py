"""Advanced CSV/Excel toolkit: dedup columns, pivot, filter, stats."""
import os, sys, argparse, csv
from collections import Counter, defaultdict

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []
    return headers, rows

def dedup_rows(path, key_col, output=None):
    headers, rows = read_csv(path)
    seen = set()
    unique = []
    for r in rows:
        val = r.get(key_col, "")
        if val not in seen:
            seen.add(val)
            unique.append(r)
    out = output or path.replace(".csv", "_deduped.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(unique)
    print(f"Deduped: {len(rows)} -> {len(unique)} rows (by '{key_col}'). Saved: {out}")

def column_stats(path, col):
    headers, rows = read_csv(path)
    vals = [r.get(col, "") for r in rows]
    numeric = []
    for v in vals:
        try:
            numeric.append(float(v))
        except ValueError:
            pass
    print(f"Column '{col}': {len(vals)} values, {len(numeric)} numeric")
    if numeric:
        print(f"  Min: {min(numeric)}, Max: {max(numeric)}, Avg: {sum(numeric)/len(numeric):.2f}, Sum: {sum(numeric):.2f}")
    c = Counter(vals)
    print(f"  Unique values: {len(c)}")
    print(f"  Top 5: {c.most_common(5)}")

def filter_rows(path, col, value, output=None):
    headers, rows = read_csv(path)
    filtered = [r for r in rows if r.get(col, "") == value]
    out = output or path.replace(".csv", f"_filtered_{value}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(filtered)
    print(f"Filtered: {len(rows)} -> {len(filtered)} rows where {col}='{value}'. Saved: {out}")

def pivot(path, row_col, val_col, agg="count"):
    headers, rows = read_csv(path)
    groups = defaultdict(list)
    for r in rows:
        groups[r.get(row_col, "")].append(r.get(val_col, ""))
    print(f"Pivot by '{row_col}' on '{val_col}' ({agg}):")
    for k in sorted(groups):
        vals = groups[k]
        if agg == "count":
            print(f"  {k}: {len(vals)}")
        elif agg == "sum":
            nums = [float(v) for v in vals if _is_num(v)]
            print(f"  {k}: {sum(nums):.2f}")
        elif agg == "avg":
            nums = [float(v) for v in vals if _is_num(v)]
            print(f"  {k}: {sum(nums)/len(nums):.2f}" if nums else f"  {k}: N/A")

def _is_num(v):
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False

def main():
    ap = argparse.ArgumentParser(description="Advanced CSV toolkit")
    sub = ap.add_subparsers(dest="cmd")
    p1 = sub.add_parser("dedup", help="Remove duplicate rows by key column")
    p1.add_argument("file"); p1.add_argument("--key", required=True); p1.add_argument("--output")
    p2 = sub.add_parser("stats", help="Column statistics")
    p2.add_argument("file"); p2.add_argument("--col", required=True)
    p3 = sub.add_parser("filter", help="Filter rows by column value")
    p3.add_argument("file"); p3.add_argument("--col", required=True); p3.add_argument("--value", required=True); p3.add_argument("--output")
    p4 = sub.add_parser("pivot", help="Pivot table")
    p4.add_argument("file"); p4.add_argument("--row", required=True); p4.add_argument("--val", required=True); p4.add_argument("--agg", default="count", choices=["count", "sum", "avg"])
    args = ap.parse_args()

    if args.cmd == "dedup":
        dedup_rows(args.file, args.key, args.output)
    elif args.cmd == "stats":
        column_stats(args.file, args.col)
    elif args.cmd == "filter":
        filter_rows(args.file, args.col, args.value, args.output)
    elif args.cmd == "pivot":
        pivot(args.file, args.row, args.val, args.agg)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
