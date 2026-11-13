# Fiverr Gig Kit — 3 gigs built from the same product

The scripts in this pack aren't just a product — they're your **delivery engine** for freelance gigs.
Each gig below takes 10–20 minutes to fulfill using GrabKit. Price them low to win first
reviews, raise after 3 reviews.

---

## Gig 1 — "I will organize and clean up your messy computer folders"
**Price:** $15 · **Delivery:** 1 day
**Buyer instructions:** "Send me a screenshot of your messy folder + tell me how you want it
sorted. I'll send back an organized structure preview; after your OK, you send me the files
in a zip and I return the organized zip."
**Fulfillment with GrabKit:** `file_organizer.py --dry-run` for the preview, then apply +
`duplicate_finder.py` + `folder_size.py` report as a bonus. ~15 min.

## Gig 2 — "I will bulk rename, resize or convert your files and photos"
**Price:** $20 · **Delivery:** 1 day
**Buyer instructions:** "Send your files (up to 1,000) + what you want done: numbered names,
lowercase, resize for email/web, convert to JPG/PNG/WebP, compress PDFs, merge PDFs."
**Fulfillment:** `bulk_rename.py`, `image_resizer.py`, `pdf_toolkit.py` — pick the right
tool, run, verify, return zip. ~20 min.

## Gig 3 — "I will merge, split or clean up your PDF files"
**Price:** $15 · **Delivery:** 1 day
**Buyer instructions:** "Tell me what you need: merge N PDFs into one, split one PDF into
pages, extract specific pages, or get an info report."
**Fulfillment:** `pdf_toolkit.py` covers all four. ~10 min.

---

## Gig 4 — Full Pack delivery (copy/paste ready)
See `SALES-KIT/fiverr-gig-full-pack.md` — complete copy (title, 3 pricing tiers $15/$29/$59, description, requirements, gallery, minor-disclosure line) for selling GrabKit as a service via Fiverr delivery.

## Gig checklist (once per gig)
1. Create gig with the title above, category: Programming & Tech → Desktop Applications or File Conversion
2. Add 3 gallery images from `GIG-IMAGES/`: e.g. gig-cover.png, gig-organizer.png, pdf-cover.png (or etsy-inside.png for the 12-tool view)
3. Set requirements: ask buyer for files + a one-line description of the job
4. Turn on "Express delivery" if available

## Why Fiverr alongside Gumroad
- Gumroad = passive (needs traffic, slower first sale)
- Fiverr = active (buyers are already searching; a $15–20 gig with a clear title usually
  gets first orders within days) — **this is the more likely path to $50 today/tomorrow**
