# GrabKit Admin — order desk with one-click delivery

Local app for your PC. No server, no hosting bill, no third-party dashboard.
Buyer order → you confirm the money → the ZIP is emailed automatically.

```
order email  →  [Sync inbox]  →  order row appears
             →  money on the card
             →  [Confirm payment & send]  →  ZIP in the buyer's inbox
```

## Install (once, ~10 minutes)

1. Double-click **`Start Admin.bat`**. The window opens with an empty order list.
2. Click **Settings → Email** and fill in:
   - `SMTP host` — `smtp.gmail.com`, port `465`
   - `Your email` — `sviatpukas21@gmail.com`
   - `App password (SMTP)` — see step 3
   - `IMAP host` — `imap.gmail.com`, `Inbox email` — the same address
   - `App password (IMAP)` — the same app password
3. **Gmail app password** (normal password will NOT work):
   - Google Account → Security → turn on **2-Step Verification**
   - then https://myaccount.google.com/apppasswords → create "GrabKit" → copy the 16 characters
4. **Settings → Products** — check that `File to send` points at the real
   `GrabKit-Desktop-v1.1.zip` (the `…` button picks it).
5. Leave **Dry run** ticked. Press **Test email** → it writes a `.eml` file into
   `admin/outbox/` instead of sending. Open it — the ZIP must be attached.
6. Untick **Dry run**, press **Test email** again to your own address, confirm the
   attachment arrives. Now you are live.

## Daily use

- **New order** — manual entry (or paste the buyer's message, press "Read from text").
- **Sync inbox** — imports unread emails with subject starting `ORDER:` straight from Gmail.
  Safe to press repeatedly: the same email is never imported twice.
- **Confirm payment & send** — only press after you see the money **in the bank app**
  (never trust a screenshot from the buyer). It emails the product and marks the order
  delivered with a timestamp.
- **Mark paid only** — money arrived but you want to send later.
- **Export CSV** — opens in Excel for your records.

## What the buyer sees

1. On `pro.html` they press **Order by email** — their mail app opens with
   subject `ORDER: GrabKit Desktop` and the fields Name / Email / OS / What to clean up.
2. You press **Sync inbox** → the order appears in the table, marked **New — not paid**.
3. Money lands on the card. You press **Confirm payment & send**.
4. They get an email with the ZIP attached and the setup instructions in the body.
   The order turns green and gets a delivery timestamp.

## Safety rules the app cannot enforce for you

1. Never ship on a screenshot. Check your bank app: amount and sender.
2. Never send CVV, SMS codes or card expiry to anyone.
3. If an order email asks for a refund, a "test payment" or a different card — it is a
   scam attempt. Delete it.

## Files (all local, never published)

| File | What it is |
|---|---|
| `config.json` | SMTP/IMAP settings + app password + email template |
| `orders.db` | SQLite database with every order |
| `outbox/` | Dry-run emails (open with any mail client) |
| `admin.log` | Timestamped log of everything the app did |

These are in `.gitignore`. Do not upload them anywhere and do not send `config.json`
to anyone — it contains your app password.

## If email does not send

- `SMTPAuthenticationError` → wrong app password, or 2-Step Verification is off.
- Timeout → provider blocks port 465; try port 587.
- "ZIP not found" → Settings → Products → pick the file again (it moved).
- Still stuck → set Dry run back on and use the outbox `.eml` to send manually until fixed.
