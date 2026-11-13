#!/usr/bin/env python3
"""link_scraper.py - extract all links from a web page.

Uses the 'requests' library when it is installed, and falls back to the
standard library (urllib) otherwise - so the script always works.
Optional checks can slow things down but nothing is installed.

Usage examples:
    python link_scraper.py https://example.com
    python link_scraper.py https://example.com --internal-only --csv links.csv
    python link_scraper.py https://example.com --status

Exit codes: 0 = page fetched, 1 = fatal error, 2 = the page could not be
fetched (bad URL, no network, HTTP error).
"""

import argparse
import csv
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

USER_AGENT = "Mozilla/5.0 (compatible; GrabKit/1.0; link scraper)"
DEFAULT_TIMEOUT = 15  # seconds for fetching the page itself
CHECK_TIMEOUT = 5     # seconds per HEAD check in --status mode

# Uses requests when available; urllib fallback otherwise.
try:
    import requests
except ImportError:
    requests = None
import urllib.error
import urllib.request


def fetch_page(url):
    """Download a page's HTML. Returns the text or exits with code 2."""
    if requests is not None:
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT},
                                    timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as exc:
            print("Error: could not fetch %s (%s)" % (url, exc))
            sys.exit(2)
    else:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
                # Decode bytes into text with a forgiving fallback encoding.
                data = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                try:
                    return data.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    return data.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            print("Error: could not fetch %s (HTTP %s: %s)" % (url, exc.code, exc.reason))
            sys.exit(2)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print("Error: could not fetch %s (%s)" % (url, exc))
            sys.exit(2)


class LinkCollector(HTMLParser):
    """Collects <a href="..."> targets plus their visible text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []          # list of (href, text)
        self._href = None        # href of the <a> currently open
        self._text_parts = []    # text inside the current <a>

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href and href.strip():
            self._href = href.strip()
            self._text_parts = []

    def handle_data(self, data):
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            text = " ".join("".join(self._text_parts).split())
            self.links.append((self._href, text))
            self._href = None
            self._text_parts = []


def clean_links(raw_links, base_url):
    """Resolve relative URLs, drop junk links. Returns a list of (url, text)."""
    base = urlparse(base_url)
    cleaned = []
    for href, text in raw_links:
        if href.startswith(("javascript:", "mailto:", "tel:", "data:", "#")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if not parsed.netloc:
            continue
        cleaned.append((absolute, text))
    # Same page anchor (#section) collapses to the same URL; that is fine,
    # --unique handles duplicates.
    return cleaned


def head_check(url):
    """HEAD-check one URL. Returns a status string like '200' or an error note."""
    if requests is not None:
        try:
            response = requests.head(url, headers={"User-Agent": USER_AGENT},
                                     timeout=CHECK_TIMEOUT,
                                     allow_redirects=True)
            return str(response.status_code)
        except requests.exceptions.RequestException as exc:
            return "error (%s)" % (exc.__class__.__name__)
    else:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT},
                                         method="HEAD")
        try:
            with urllib.request.urlopen(request, timeout=CHECK_TIMEOUT) as response:
                return str(response.getcode())
        except urllib.error.HTTPError as exc:
            return str(exc.code)
        except urllib.error.URLError as exc:
            # A site may refuse HEAD; say so plainly instead of a traceback.
            return "error (%s)" % getattr(exc.reason, "__class__.__name__", "URLError")
        except (OSError, ValueError):
            return "error"


def main():
    parser = argparse.ArgumentParser(
        prog="link_scraper.py",
        description="Extract all links from a web page, optionally check them "
                    "and export to CSV.",
        epilog="Examples:\n"
               "  python link_scraper.py https://example.com\n"
               "  python link_scraper.py https://example.com --internal-only --csv links.csv\n"
               "  python link_scraper.py https://example.com --status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="the web page to scrape, e.g. https://example.com")
    parser.add_argument("--internal-only", action="store_true",
                        help="only keep links on the same site")
    parser.add_argument("--no-unique", dest="unique", action="store_false",
                        help="keep duplicate links instead of collapsing them")
    parser.set_defaults(unique=True)
    parser.add_argument("--csv", metavar="FILE",
                        help="also write the links to a CSV file (columns: url,text)")
    parser.add_argument("--status", action="store_true",
                        help="check every link (HEAD request) and show its status code")
    args = parser.parse_args()

    url = args.url.strip()
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        print("Error: please give a full URL starting with http:// or https://")
        print('Example: python link_scraper.py "https://example.com"')
        sys.exit(2)

    if requests is None:
        print("Note: 'requests' not installed - using the built-in fallback.")
        print("(Optional: pip install requests)")

    html = fetch_page(url)

    collector = LinkCollector()
    try:
        collector.feed(html)
        collector.close()
    except Exception as exc:
        print("Error: could not parse the page as HTML (%s)." % exc)
        sys.exit(2)

    links = clean_links(collector.links, url)

    if args.internal_only:
        base_host = urlparse(url).netloc.lower()
        links = [(u, t) for (u, t) in links if urlparse(u).netloc.lower() == base_host]

    if args.unique:
        seen = set()
        unique_links = []
        for u, t in links:
            if u not in seen:
                seen.add(u)
                unique_links.append((u, t))
        links = unique_links

    if not links:
        print("No links found on %s." % url)
        return  # not an error: the page simply has no links

    if args.csv:
        csv_path = Path(args.csv)
        try:
            with csv_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["url", "text"])
                for u, t in links:
                    writer.writerow([u, t])
            print("Saved %d links to %s" % (len(links), csv_path))
        except (PermissionError, OSError) as exc:
            print("Error: cannot write CSV file '%s' (%s)" % (csv_path, exc))
            print("Continuing without the CSV export.")

    for u, t in links:
        if args.status:
            status = head_check(u)
            label = t if t else "(no text)"
            print("[%s] %s  (%s)" % (status, u, label))
        else:
            label = t if t else "(no text)"
            print("%s  (%s)" % (u, label))

    print("")
    print("Total: %d link%s on %s" % (len(links), "" if len(links) == 1 else "s", url))
    if requests is None:
        print("Tip: 'pip install requests' makes this tool faster and more reliable.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
