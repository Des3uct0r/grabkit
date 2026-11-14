# GrabKit Admin — orders and delivery in one window

Double-click **`Start Admin.bat`**. That is the whole installation.
No server, no account, no password required.

## The 3-click flow (default, works immediately)

1. Buyer writes to you (email, OLX, Telegram) — copy their message.
2. In the app: **Add order** → paste → **Add order**. The buyer's email is found
   automatically. (If Gmail is set up, **Sync inbox** does this step by itself.)
3. Money is on the card → select the order → **Confirm payment & send**.

In this mode the app opens a finished email in your mail app with the ZIP already
attached — you only press **Send**. No SMTP password, no configuration.

If no mail app is installed, it copies the message text and opens the folder with the
ZIP selected, so you can paste it into Telegram and drag the file in.

## Optional: fully automatic sending

Only if you want the app to send without opening your mail client.

**Setup →** two fields: your email and an app password → **Save & send test**.
After that the status line says `AUTO` and the same button sends silently.

> ⚠️ **Some Google accounts cannot create app passwords.** School, university and
> company (Workspace) accounts usually block it: the page says
> *"App passwords are not available for your account"*. If you see that, stay in the
> default manual mode — it works identically, just with one extra click.
> Other options: a second personal @gmail.com, or a free sending service such as
> Brevo (SMTP host `smtp-relay.brevo.com`, port 587) — then set the host manually in
> `config.json`.

## What the app does for you

| Button | What happens |
|---|---|
| **Sync inbox** | Imports unread `ORDER:` emails into the list. Never duplicates an email. |
| **Confirm payment & send** | Sends (or opens) the product email, marks the order delivered with a timestamp. |
| **Mark paid only** | Money arrived, send later. |
| **No email? Deliver by hand** | Same delivery, but always manual. |
| **Export CSV** | Orders in Excel. |

Order statuses: `New — not paid` → `Paid` → `Delivered`. New rows are yellow, delivered
rows are green.

## Two rules that protect you

1. **Only press the green button after you see the money in the bank app.** Never trust
   a screenshot — they are easy to fake.
2. **Never send card numbers, CVV or SMS codes to a buyer.** For an incoming payment
   none of that is ever needed.

## Files (local only, never uploaded)

| File | What it is |
|---|---|
| `config.json` | settings and (if you set it up) the app password |
| `orders.db` | every order |
| `outbox/` | generated emails/drafts |
| `admin.log` | what the app did and when |

All four are in `.gitignore`. Do not send `config.json` to anyone.
