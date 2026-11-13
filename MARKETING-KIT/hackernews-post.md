# Hacker News — Show HN Post

**Title:** Show HN: GrabKit – 12 stdlib-first Python scripts for file automation (dry-run safe)

**Body:**
I packaged 12 small automation scripts I've written for myself over the years into a $9.99 digital product. 9 use only stdlib; 3 need a one-line pip install.

The design focus is safety: every destructive operation previews first and requires confirmation. Nothing is deleted or overwritten without explicit OK + .bak backups where applicable.

Tools: file organizer, duplicate finder (content-hash based), folder size analyzer, backup zip, bulk rename, find & replace, CSV toolkit, text diff, PDF toolkit (merge/split/extract), image resizer, link scraper, password tools.

I'm sharing because the "safety-first CLI tool" pattern worked well for non-technical buyers — the dry-run preview is the feature they mention most.

Gumroad: [LINK]
Partial repo: [GITHUB LINK]

Happy to discuss the implementation (two-pass hashing for dedup, cross-platform path handling, etc.).
