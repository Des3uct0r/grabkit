# Etsy Setup — GrabKit in Ukraine (withdrawing to a Ukrainian bank)

Verified Nov 2026 against Etsy's own help center and fees pages: https://help.etsy.com/hc/en-us/articles/115014503608-How-to-Get-Paid-on-Etsy and https://www.etsy.com/legal/etsy-payments/

## Why Etsy (and only Etsy) for Ukraine
- Etsy Payments in Ukraine works **only via Payoneer Payment Account** (USD, weekly Monday payouts).
- PayPal commercial payments to Ukraine are blocked — Gumroad, Ko-fi, Payhip, Sellfy all route through PayPal/Stripe and are dead ends for you.
- Fees: listing $0.20 + transaction 6.5% + payment processing 6% + $0.30 per order. On $9.99 you keep ~$8.24.
- Fiverr is also viable to Ukraine via Payoneer.

## What you need to do (in your own browser — Etsy is blocked from the agent's browser)

### Step 1 — Payoneer (free signup, ~15 min)
1. Go to https://www.payoneer.com/go/ (already opened in the browser)
2. Sign up as an **individual freelancer/seller** with your legal name, date of birth, Ukrainian address, email and phone
3. Verify your ID (Passport/ID card) — this KYC step is why only you can do it
4. Get your Payoneer Payment Account approved (emails: up to 1–3 days)

### Step 2 — Etsy shop (~20 min, $0.20 listing fee)
1. In your browser open https://www.etsy.com/sell
2. Create the shop (name suggestion: "GrabKitTools"), select Ukraine as your shop country
3. Link your Payoneer Payment Account when prompted for payment settings
   (Shop Manager → Finances → Payment settings → Enroll now → Payoneer)
4. Set shop policies: 30-day refund, personal & commercial license (no resale)

### Step 3 — Create the listing
Use `SALES-KIT/etsy-listing.md` (copy/paste ready):
- **Title**: from file
- **13 tags**: python scripts, file organizer, duplicate finder, bulk rename, photo resizer, pdf merger, automation tools, digital download, productivity, file management, backup tool, csv tools, no coding
- **Category**: Digital Downloads > Software & Apps > Utilities
- **Price**: $9.99
- **Images**: `GIG-IMAGES/etsy-hero.png` (main), `etsy-inside.png`, `etsy-how.png`
- **File to attach**: `C:\x\mm\GrabKit-v1.zip` (Digital software files section)

### Step 4 — First sales flow
1. Send traffic: the DEV.to article (already published) and the GitHub Pages site (CTA now points to the release) → swap CTAs to the Etsy link once live
2. Fiverr Gigs remain the other live channel

## Status
- Etsy listing copy: ready (`SALES-KIT/etsy-listing.md`)
- Etsy listing images: ready (`GIG-IMAGES/etsy-hero.png`, `etsy-inside.png`, `etsy-how.png`)
- Etsy file: ready (`GrabKit-v1.zip`)
- Blocked on: your Payoneer signup + Etsy shop creation (both need your identity/bank details — cannot be automated or faked)

## Alternative: Freelancehunt (Ukrainian clients, UAH cards)
- Ukraine-based marketplace (freelancehunt.com), 1.2M+ freelancers, escrow (Сейф) for every project, funds released to your card on completion
- UAH payouts to a Ukrainian Visa/Mastercard (5% withdrawal fee), USD/EUR via Payoneer for foreign clients, invoice via "Фриланс Рахунок" (Freelancehunt issues invoices on your behalf as a European legal entity — works even for clients found outside FH)
- Verification is via Ukrainian documents: passport / driver's license / BankID / Дія.Підпис — practically an 18+ workflow
- 0% project commission; 5% withdrawal fee; min. project budget 500–700 UAH
- Account flow: register as freelancer → profile verification → fill portfolio (3 works) → bid on projects → client reserves funds via Сейф → you deliver → funds to your card
- For a minor: needs a parent/legal guardian's account or BankID-compatible adult supervision — same 18+ constraint as everywhere

## Alternative: Upwork (international, highest value)
- UPWORK is 18+, **no guardian route** — only available once you turn 18
- Verification via ID; payout via Payoneer/bank/wire; hourly or fixed-price
- Highest pay, most competition, hardest to win without reviews — realistic path is Fiverr/Freelancehunt first, build portfolio, Upwork at 18+

## Gumroad — removed
Gumroad was ruled out (Ukraine payout blocked; account can't publish). All repo links updated to the GitHub release / GitHub Pages.
