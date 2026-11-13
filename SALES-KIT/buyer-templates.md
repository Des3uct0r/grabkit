# Buyer Response Templates & Order Fulfillment

Paste these as-is, swapping the bracketed parts. Keep all communication **inside Fiverr chat**.

---

## 1. First reply (send within 1 hour of any inquiry — this is your ranking lever)

> Hi [name]! Thanks for reaching out. I can absolutely handle this.
>
> Quick check before I start: could you send me [the files / a download link] plus one line on what you want done (e.g. "rename to 001.jpg style", "resize to max width 1200", "merge into one PDF")?
>
> Once I have that, I'll send you a preview plan before touching anything, and you'll get the finished files within [1 / 2 / 3] day(s).
>
> — [your name]

## 2. After you receive the files (confirm + preview)

> Got everything, thanks! Here's my plan:
>
> - [e.g. 340 photos → numbered 001.jpg … 340.jpg, kept in original order]
> - [e.g. resized to max width 1200px, converted to WebP]
>
> Nothing has been changed yet. Reply "go" and I'll run it; any tweaks to the plan, tell me now.
>
> Originals are untouched — I work on copies only.

## 3. Delivery message (when you send the result)

> All done! Here's your finished [zip / folder link].
>
> What I did:
> - [bullet 1]
> - [bullet 2]
>
> A couple of notes:
> - Originals are untouched in your copy.
> - If anything looks off, reply here and I'll fix it within 24 hours (revisions are included).
>
> If this saved you time, a quick review means a lot to a new seller. Thanks for trusting me with this!

## 4. Revision request (keep it warm, no defensiveness)

> No problem at all — send me the exact change you want and I'll redo it. Could you point to the specific file(s) or the exact rule that should change (e.g. "start numbering at 0001 instead of 001")? That way I get it right the first time.

## 5. Declining an off-platform / suspicious request (polite, firm)

> Thanks for the offer! I keep all work and payments inside Fiverr so both of us are protected by their buyer/seller guarantees — it's also what lets me offer the revision policy.
>
> If you'd like to proceed here, just place the order on the gig and we'll get started right away. Happy to help either way.

## 6. When a buyer sends a file you don't trust

> Thanks for sending this! Before I open it — could you confirm what this file is / where it came from? I'm cautious about running unknown executables or macros for security reasons, but standard documents (PDF, JPG, PNG, ZIP of docs) are fine on my end.
>
> If it's an unusual format, a screenshot of what you need or a sample in a standard format works too.

---

## Per-order fulfillment checklist (do this every time)

**Before you start**
- [ ] Buyer's request matches one of your gig packages (if bigger, upsell in chat first)
- [ ] Files received or download link works
- [ ] Downloaded files to a **dedicated working folder** — never run anything from your Downloads root
- [ ] If any file is `.exe`, `.bat`, `.ps1`, `.vbs`, `.js`, `.scr`, `.dll` → stop and ask the buyer (see template 6). Don't open it.
- [ ] If a link is from an unknown domain → don't click; ask the buyer to attach the files or use Drive/Dropbox/WeTransfer

**Run the job**
- [ ] Make a copy of the buyer's files in a "work" subfolder; originals stay untouched
- [ ] Run the GrabKit script with `--dry-run` first; send the preview plan to the buyer (template 2)
- [ ] Wait for "go" before applying
- [ ] Apply with `--backup` (creates `.bak` copies) whenever find_replace or bulk edits are involved
- [ ] Verify output: spot-check 3–5 files, count matches the input count
- [ ] Zip the result; name it `[buyername]-[job]-[date].zip`

**Deliver**
- [ ] Upload the zip to Fiverr (or attach if < 100 MB; use a Drive link for bigger)
- [ ] Send template 3 with a short bullet list of what you did
- [ ] Mark the order as delivered in Fiverr (don't skip this — it triggers the review prompt)

**After delivery**
- [ ] If buyer is silent for 3 days, send one polite nudge: "Just checking in — did everything work out? Happy to tweak anything."
- [ ] If a revision comes in, do it within 24 h and send template 4
- [ ] Log the order in a simple spreadsheet: date, buyer, gig, amount, time spent (so you know your real hourly rate)

## Security rules (non-negotiable)

1. **Never run buyer-provided executables or scripts.** No `.exe`, `.bat`, `.ps1`, `.vbs`, `.js`, `.scr`, macro-enabled Office files. If a buyer needs automation, you write it yourself from their description.
2. **Never click buyer links to install software.** Find tools yourself from official sources.
3. **Never move payments off Fiverr.** No PayPal, no crypto, no gift cards, no "I'll pay you directly."
4. **Never share your email, phone, or socials** — keep it in Fiverr chat.
5. **Work on copies only.** Buyer's originals stay in a "received" folder, untouched.
6. **If something feels wrong, decline politely** (template 5). A lost $20 order is nothing; a compromised machine or banned account is everything.

## Time budget per order (to keep it profitable)

| Gig | Typical time | At $15–20 | Effective rate |
|---|---|---|---|
| Gig 1 (rename/resize/convert) | 10–20 min | $20 | $60–120/h |
| Gig 2 (PDF merge/split) | 5–10 min | $15 | $90–180/h |

If an order takes more than 30 minutes, message the buyer before delivery to agree on scope — don't silently eat the time.
