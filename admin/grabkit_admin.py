#!/usr/bin/env python3
"""GrabKit Admin — local order desk with one-click delivery.

Buyer sends an email with subject "ORDER: ..." → press "Sync inbox" → the order shows
up here → when the money is on the card, press "Confirm payment & send" → the buyer
gets the ZIP by email automatically.

Runs entirely on this computer. No server, no monthly fee, no third-party access to
your inbox beyond the app password you paste in Settings.

Requires Python 3.8+ with tkinter (included in the official installer).
"""

import base64
import csv
import ctypes
import imaplib
import json
import os
import re
import ssl
import smtplib
import sqlite3
import subprocess
import sys
import threading
import traceback
import webbrowser
from datetime import datetime
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from pathlib import Path
from urllib.parse import quote

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:  # pragma: no cover
    sys.stderr.write("tkinter is missing — reinstall Python from python.org.\n")
    raise SystemExit(1)

APP_NAME = "GrabKit Admin"
VERSION = "1.0"
HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
DB_PATH = HERE / "orders.db"
OUTBOX = HERE / "outbox"
LOG_PATH = HERE / "admin.log"

STATUS_LABELS = {
    "new": "New — not paid",
    "paid": "Paid",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}

DEFAULT_CONFIG = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 465,
    "smtp_user": "sviatpukas21@gmail.com",
    "smtp_password": "",
    "from_name": "Sviatoslav — GrabKit",
    "imap_host": "imap.gmail.com",
    "imap_user": "sviatpukas21@gmail.com",
    "imap_password": "",
    "order_subject_prefix": "ORDER:",
    "dry_run": True,
    "products": {
        "GrabKit Desktop": {
            "price": "249 UAH",
            "file": r"C:\x\mm\GrabKit-Desktop-v1.1.zip",
        },
    },
    "template": (
        "Hi {name},\n\n"
        "Payment received — thank you!\n\n"
        "Attached is {product} ({price}). Inside:\n"
        "  • Start GrabKit.bat — double-click to open the app\n"
        "  • README-UK.md — instructions in Ukrainian\n"
        "  • README.md — instructions in English\n"
        "  • 16 tools in the scripts folder\n\n"
        "How to start: unzip the archive anywhere (for example Desktop), then\n"
        "double-click Start GrabKit.bat. Pick a tool on the left, pick your folder,\n"
        "press Run.\n\n"
        "If anything does not open, just reply to this email — I will fix it with you.\n"
        "And if it is not what you expected, reply within 30 days and I refund you,\n"
        "no questions asked.\n\n"
        "Enjoy,\n"
        "Sviatoslav\n"
        "GrabKit\n"
    ),
}


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def log_line(text):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write("[%s] %s\n" % (now(), text))
    except OSError:
        pass


def decode_mime(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # broken headers happen; never crash the sync
        return value


def load_config():
    config = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            config.update(saved)
            config["products"] = {**DEFAULT_CONFIG["products"],
                                  **saved.get("products", {})}
        except (OSError, ValueError):
            pass
    return config


def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False),
                           encoding="utf-8")


def autodetect_product(config):
    """Find the ZIP to sell without asking the user to browse for it."""
    products = config.setdefault("products", {})
    info = products.setdefault("GrabKit Desktop", {"price": "249 UAH", "file": ""})
    if Path(info.get("file", "")).is_file():
        return config
    folders = [HERE / "product", HERE, HERE.parent, Path.home() / "Desktop"]
    for folder in folders:
        if not folder.is_dir():
            continue
        for cand in sorted(folder.glob("*.zip")):
            name = cand.name.lower()
            if "grabkit" in name and "desktop" in name:
                info["file"] = str(cand)
                return config
    return config


def connect_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE IF NOT EXISTS orders (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               created_at TEXT NOT NULL,
               name TEXT,
               email TEXT NOT NULL,
               product TEXT NOT NULL,
               amount TEXT,
               status TEXT NOT NULL DEFAULT 'new',
               message_id TEXT UNIQUE,
               note TEXT,
               delivered_at TEXT
           )"""
    )
    db.commit()
    return db


# ----------------------------------------------------------------------------
# order parsing / syncing
# ----------------------------------------------------------------------------
FIELDS = {
    "name": ("name", "імя", "имя", "ім'я"),
    "os": ("os", "система", "операційна"),
    "note": ("what i want to clean up", "what do you need", "деталі", "задача",
             "що прибрати", "коментар"),
}


def parse_order(subject, sender, body):
    """Extract an order dict from an email. Never raises."""
    product = "GrabKit Desktop"
    prefix = "ORDER:"
    match = re.search(r"order\s*:?\s*(.+)", subject or "", re.I)
    if match:
        product = match.group(1).strip() or product

    email_addr = parseaddr(sender or "")[1].strip().lower()
    name = ""
    fields = {}
    for raw_line in (body or "").splitlines():
        line = raw_line.strip().lstrip("-•* ").strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if not value:
            continue
        for field, names in FIELDS.items():
            if key in names:
                fields[field] = value
    name = fields.get("name", "")
    note = fields.get("note", "")
    if fields.get("os"):
        note = (note + " | OS: " + fields["os"]).strip(" |")
    return {"product": product, "email": email_addr, "name": name, "note": note}


def imap_sync(config, progress):
    """Import unread ORDER: emails. Returns (added, skipped, error)."""
    host = config.get("imap_host") or ""
    user = config.get("imap_user") or ""
    password = config.get("imap_password") or ""
    if not (host and user and password):
        return 0, 0, "IMAP is not configured (Settings → Inbox)"

    added = skipped = 0
    db = connect_db()
    try:
        box = imaplib.IMAP4_SSL(host, ssl_context=ssl.create_default_context())
        box.login(user, password)
        box.select("INBOX", readonly=False)
        typ, data = box.search(None, 'UNSEEN', 'SUBJECT', '"%s"' %
                               config.get("order_subject_prefix", "ORDER:"))
        if typ != "OK":
            return 0, 0, "IMAP search failed: %s" % typ
        ids = data[0].split()
        progress("Found %d unread order email(s)." % len(ids))
        for num in ids:
            typ, raw = box.fetch(num, "(RFC822)")
            if typ != "OK" or not raw or not isinstance(raw[0], tuple):
                continue
            msg = message_from_bytes(raw[0][1])
            message_id = (msg.get("Message-ID") or "").strip()
            subject = decode_mime(msg.get("Subject"))
            sender = decode_mime(msg.get("From"))
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True) or b""
                        body = payload.decode(part.get_content_charset() or "utf-8",
                                              errors="replace")
                        break
            else:
                payload = msg.get_payload(decode=True) or b""
                body = payload.decode(msg.get_content_charset() or "utf-8",
                                      errors="replace")

            order = parse_order(subject, sender, body)
            if not order["email"]:
                skipped += 1
                continue
            try:
                db.execute(
                    "INSERT INTO orders (created_at, name, email, product, amount,"
                    " status, message_id, note) VALUES (?,?,?,?,?,?,?,?)",
                    (now(), order["name"], order["email"], order["product"],
                     config["products"].get(order["product"], {}).get("price", ""),
                     "new", message_id or None, order["note"]),
                )
                db.commit()
                added += 1
                box.store(num, "+FLAGS", "\\Seen")
            except sqlite3.IntegrityError:
                skipped += 1  # already imported
                box.store(num, "+FLAGS", "\\Seen")
        box.logout()
        return added, skipped, None
    except Exception as exc:  # network, auth, TLS — report, do not crash
        return added, skipped, "%s: %s" % (exc.__class__.__name__, exc)
    finally:
        db.close()


# ----------------------------------------------------------------------------
# sending
# ----------------------------------------------------------------------------
def build_email(config, order):
    products = config.get("products", {})
    product = order["product"]
    info = products.get(product)
    if not info:
        return None, None
    price = order["amount"] or info.get("price", "")

    msg = EmailMessage()
    msg["Subject"] = "Your %s - payment received" % product
    msg["From"] = formataddr((config.get("from_name", "GrabKit"),
                              config.get("smtp_user", "")))
    msg["To"] = order["email"]

    name = order["name"] or "there"
    text = config.get("template", DEFAULT_CONFIG["template"]).format(
        name=name, product=product, price=price)
    msg.set_content(text)

    path = Path(info.get("file", ""))
    if path.is_file():
        data = path.read_bytes()
        msg.add_attachment(data, maintype="application", subtype="zip",
                           filename=path.name)
    return msg, path


def build_test_message(config):
    msg = EmailMessage()
    msg["Subject"] = "GrabKit Admin — test message"
    msg["From"] = formataddr((config.get("from_name", "GrabKit"),
                              config.get("smtp_user", "")))
    msg["To"] = config.get("smtp_user", "")
    msg.set_content(
        "This is a test from GrabKit Admin.\n\n"
        "If you can read this, the order desk will now deliver files to buyers "
        "automatically when you press the green button.\n")
    return msg


def send_email(config, msg):
    host = config.get("smtp_host")
    port = int(config.get("smtp_port") or 465)
    user = config.get("smtp_user")
    password = config.get("smtp_password")
    if not (host and user and password):
        raise RuntimeError("SMTP is not configured (Settings → Email)")
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=30,
                                  context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
    try:
        server.login(user, password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass


def deliver(config, order, progress):
    """Send the product to the buyer. Returns a status string."""
    msg, path = build_email(config, order)
    if msg is None:
        return ("Product '%s' is not configured — add it in Settings → Products "
                "with the file to send." % order["product"])
    if not path.is_file():
        return "ZIP not found: %s — fix it in Settings → Products" % path
    if config.get("dry_run"):
        OUTBOX.mkdir(exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9@._-]", "_", order["email"])
        target = OUTBOX / ("%s_%s.eml" % (datetime.now().strftime("%Y%m%d-%H%M%S"), safe))
        target.write_bytes(msg.as_bytes())
        progress("DRY RUN — email written to %s (nothing sent)." % target.name)
        return "dry-run"
    send_email(config, msg)
    progress("Sent to %s with %s." % (order["email"], path.name))
    return "sent"


# ----------------------------------------------------------------------------
# GUI
# ----------------------------------------------------------------------------
class AdminApp:
    def __init__(self, root):
        self.root = root
        self.config = autodetect_product(load_config())
        save_config(self.config)
        self.db = connect_db()
        self.selected = None
        self.busy = False
        self._build()
        self.refresh()
        if self.config.get("smtp_password") and self.config.get("imap_password"):
            self.root.after(1200, self.sync)

    # ---------- layout ----------
    def _build(self):
        root = self.root
        root.title("%s %s" % (APP_NAME, VERSION))
        root.geometry("1080x720")
        root.minsize(900, 600)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Muted.TLabel", foreground="#57606a")
        style.configure("Send.TButton", font=("Segoe UI", 10, "bold"))

        top = ttk.Frame(root, padding=(14, 10, 14, 4))
        top.pack(fill="x")
        ttk.Label(top, text=APP_NAME, style="Title.TLabel").pack(side="left")
        self.mode = ttk.Label(top, text="", style="Muted.TLabel")
        self.mode.pack(side="left", padx=(12, 0))
        ttk.Button(top, text="Setup", command=self.open_settings
                   ).pack(side="right")
        ttk.Button(top, text="Send test", command=self.test_email
                   ).pack(side="right", padx=(0, 6))
        self.sync_btn = ttk.Button(top, text="Sync inbox", command=self.sync)
        self.sync_btn.pack(side="right", padx=(0, 6))
        ttk.Button(top, text="New order", command=self.new_order
                   ).pack(side="right", padx=(0, 6))
        ttk.Button(top, text="Export CSV", command=self.export_csv
                   ).pack(side="right", padx=(0, 6))

        # --- orders table
        table_frame = ttk.Frame(root, padding=(14, 8))
        table_frame.pack(fill="both", expand=True)
        columns = ("date", "email", "product", "amount", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                 selectmode="browse", height=12)
        widths = {"date": 130, "email": 240, "product": 200, "amount": 100,
                  "status": 130}
        titles = {"date": "Received", "email": "Buyer", "product": "Product",
                  "amount": "Amount", "status": "Status"}
        for col in columns:
            self.tree.heading(col, text=titles[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(table_frame, orient="vertical",
                               command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.tag_configure("new", background="#fff8e1")
        self.tree.tag_configure("delivered", background="#e8f5e9")

        # --- detail + actions
        detail = ttk.LabelFrame(root, text="Selected order", padding=10)
        detail.pack(fill="x", padx=14)
        self.detail = ttk.Label(detail, text="Select an order above.",
                                style="Muted.TLabel", wraplength=980,
                                justify="left")
        self.detail.pack(anchor="w")

        actions = ttk.Frame(detail)
        actions.pack(anchor="w", pady=(8, 0))
        self.send_btn = ttk.Button(actions, text="Confirm payment & send",
                                   style="Send.TButton", command=self.confirm_send,
                                   state="disabled")
        self.send_btn.pack(side="left")
        ttk.Button(actions, text="Mark paid only",
                   command=lambda: self.set_status("paid")).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Cancel order",
                   command=lambda: self.set_status("cancelled")).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Delete",
                   command=self.delete_order).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Copy email",
                   command=self.copy_email).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="No email? Deliver by hand",
                   command=self.manual_delivery).pack(side="left", padx=(8, 0))

        # --- log
        log_frame = ttk.LabelFrame(root, text="Log", padding=6)
        log_frame.pack(fill="both", padx=14, pady=(8, 12))
        self.log = tk.Text(log_frame, height=7, wrap="word",
                           font=("Consolas", 9), bg="#0d1117", fg="#d0d7de",
                           relief="flat", padx=8, pady=6)
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status_var, style="Muted.TLabel",
                  padding=(14, 0, 14, 8)).pack(fill="x")

    # ---------- data ----------
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        rows = self.db.execute(
            "SELECT * FROM orders ORDER BY CASE status WHEN 'new' THEN 0"
            " WHEN 'paid' THEN 1 WHEN 'delivered' THEN 2 ELSE 3 END, id DESC"
        ).fetchall()
        for row in rows:
            tag = "new" if row["status"] == "new" else (
                "delivered" if row["status"] == "delivered" else "")
            self.tree.insert("", "end", iid=str(row["id"]), tags=(tag,),
                             values=(row["created_at"], row["email"],
                                     row["product"], row["amount"] or "",
                                     STATUS_LABELS.get(row["status"], row["status"])))
        count = len(rows)
        new = sum(1 for r in rows if r["status"] == "new")
        self.status_var.set("%d order(s), %d waiting for payment" % (count, new))
        auto = bool(self.config.get("smtp_password")) and not self.config.get("dry_run")
        self.mode.configure(
            text="AUTO — emails are sent for you" if auto
            else "MANUAL — a ready email opens, you press Send",
            foreground="#1a7f37" if auto else "#9a6700")
        if self.selected and not self.tree.exists(str(self.selected)):
            self.selected = None
            self.detail.configure(text="Select an order above.")
            self.send_btn.configure(state="disabled")

    def current(self):
        if not self.selected:
            return None
        return self.db.execute("SELECT * FROM orders WHERE id=?",
                               (self.selected,)).fetchone()

    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected = int(sel[0])
        row = self.current()
        if row is None:
            return
        text = ("%s  <%s>\nProduct: %s   Amount: %s   Status: %s\nNote: %s"
                % (row["name"] or "no name", row["email"], row["product"],
                   row["amount"] or "—", STATUS_LABELS.get(row["status"], row["status"]),
                   row["note"] or "—"))
        if row["delivered_at"]:
            text += "\nDelivered: %s" % row["delivered_at"]
        self.detail.configure(text=text)
        self.send_btn.configure(
            state="disabled" if row["status"] == "delivered" or self.busy else "normal")

    def write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        log_line(text)

    # ---------- actions ----------
    def sync(self):
        if self.busy:
            return
        if not self.config.get("imap_password"):
            messagebox.showinfo("Inbox not configured",
                                "Open Settings and paste your Gmail app password "
                                "for the inbox (IMAP).")
            return
        self.busy = True
        self.sync_btn.configure(state="disabled")
        self.write("Syncing inbox…")

        def worker():
            try:
                added, skipped, error = imap_sync(self.config, self.write)
                if error:
                    self.write("Sync failed: " + error)
                else:
                    self.write("Imported %d new order(s), skipped %d." %
                               (added, skipped))
            except Exception:
                self.write("Sync crashed:\n" + traceback.format_exc())
            finally:
                self.busy = False
                self.root.after(0, self._after_sync)

        threading.Thread(target=worker, daemon=True).start()

    def _after_sync(self):
        self.sync_btn.configure(state="normal")
        self.refresh()

    def new_order(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add order")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("520x330")

        ttk.Label(dialog, text="Paste the buyer's message — I will find the email myself.",
                  padding=(12, 12, 12, 4)).pack(anchor="w")
        paste = tk.Text(dialog, height=8, wrap="word")
        paste.pack(fill="both", expand=True, padx=12)
        paste.focus_set()

        row = ttk.Frame(dialog, padding=12)
        row.pack(fill="x")
        ttk.Label(row, text="Product").pack(side="left")
        product_var = tk.StringVar(
            value=next(iter(self.config.get("products", {})), "GrabKit Desktop"))
        ttk.Combobox(row, textvariable=product_var, state="readonly", width=26,
                     values=list(self.config.get("products", {}))).pack(side="left", padx=8)
        hint = ttk.Label(row, text="", style="Muted.TLabel")
        hint.pack(side="left")

        def add():
            text = paste.get("1.0", "end")
            parsed = parse_order("", "", text)
            email_addr = parsed["email"]
            if "@" not in email_addr:
                found = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
                email_addr = found.group(0) if found else ""
            if "@" not in email_addr:
                hint.configure(text="No email address found — add it to the text.")
                return
            self.db.execute(
                "INSERT INTO orders (created_at, name, email, product, amount,"
                " status, note) VALUES (?,?,?,?,?,?,?)",
                (now(), parsed["name"], email_addr, product_var.get(),
                 self.config["products"].get(product_var.get(), {}).get("price", ""),
                 "new", parsed["note"]))
            self.db.commit()
            dialog.destroy()
            self.refresh()
            self.write("Order added: %s" % email_addr)

        ttk.Button(dialog, text="Add order", command=add,
                   style="Send.TButton").pack(pady=(0, 12))

    def set_status(self, status, order_id=None):
        oid = order_id or self.selected
        if not oid:
            return
        self.db.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
        self.db.commit()
        self.refresh()

    def delete_order(self):
        if not self.selected:
            return
        if not messagebox.askyesno("Delete order", "Delete this order record?"):
            return
        self.db.execute("DELETE FROM orders WHERE id=?", (self.selected,))
        self.db.commit()
        self.selected = None
        self.refresh()

    def copy_email(self):
        row = self.current()
        if row:
            self.root.clipboard_clear()
            self.root.clipboard_append(row["email"])
            self.status_var.set("Copied %s" % row["email"])

    def confirm_send(self):
        row = self.current()
        if row is None or self.busy:
            return
        if row["status"] == "delivered":
            messagebox.showinfo("Already delivered", "This order was already sent.")
            return

        auto = bool(self.config.get("smtp_password")) and not self.config.get("dry_run")
        if not auto:
            # Zero-setup path: no password needed, the mail app opens a ready draft.
            if not messagebox.askyesno(
                    "Send the product?",
                    "Money from %s (%s) is on the card?\n\n"
                    "A ready email with %s attached will open — press Send there."
                    % (row["name"] or row["email"], row["amount"] or "—",
                       row["product"])):
                return
            self.manual_delivery()
            return

        if not messagebox.askyesno(
                "Send the product?",
                "Money from %s (%s) is on the card?\n\n"
                "This will email %s to %s and mark the order delivered."
                % (row["name"] or row["email"], row["amount"] or "—",
                   row["product"], row["email"])):
            return

        self.busy = True
        self.send_btn.configure(state="disabled")
        self.write("Delivering to %s…" % row["email"])

        def worker():
            try:
                result = deliver(self.config, dict(row), self.write)
                if result in ("sent", "dry-run"):
                    self.root.after(0, lambda: self._delivered(row["id"]))
                else:
                    self.write("Not sent: " + result)
                    self.root.after(0, lambda: messagebox.showerror("Not sent", result))
            except Exception as exc:
                self.write("Send failed: %s: %s" % (exc.__class__.__name__, exc))
                self.root.after(0, lambda: messagebox.showerror(
                    "Send failed", "%s\n\nCheck Settings → Email and the app password."
                    % exc))
            finally:
                self.busy = False
                self.root.after(0, lambda: self.send_btn.configure(
                    state="normal" if self.selected else "disabled"))

        threading.Thread(target=worker, daemon=True).start()

    def _delivered(self, order_id):
        self.db.execute("UPDATE orders SET status='delivered', delivered_at=? "
                        "WHERE id=?", (now(), order_id))
        self.db.commit()
        self.refresh()
        self.status_var.set("Delivered. Order marked as sent.")

    def test_email(self):
        row = self.current()
        target = (row["email"] if row else self.config.get("smtp_user"))
        if not target:
            messagebox.showinfo("No recipient", "Select an order or set SMTP user.")
            return
        order = {"name": "test", "email": target, "product": "GrabKit Desktop",
                 "amount": "", "status": "new"}
        self.write("Test email to %s…" % target)
        try:
            result = deliver(self.config, order, self.write)
            if result in ("sent", "dry-run"):
                messagebox.showinfo("Test", "Test email %s." %
                                    ("saved to outbox" if result == "dry-run" else "sent"))
            else:
                messagebox.showerror("Test failed", result)
        except Exception as exc:
            messagebox.showerror("Test failed", "%s\n\n%s" % (exc, traceback.format_exc(limit=1)))

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")],
                                            initialfile="orders.csv")
        if not path:
            return
        rows = self.db.execute("SELECT * FROM orders ORDER BY id").fetchall()
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "created_at", "name", "email", "product",
                             "amount", "status", "delivered_at", "note"])
            for row in rows:
                writer.writerow([row[k] for k in ("id", "created_at", "name", "email",
                                                  "product", "amount", "status",
                                                  "delivered_at", "note")])
        self.write("Exported %d order(s) to %s" % (len(rows), path))

    # ---------- one-screen setup ----------
    def open_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Setup — one screen")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("560x330")
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Two fields, then you never touch this again.",
                  style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(frame, text="Your email").grid(row=1, column=0, sticky="w", pady=(14, 4))
        user_var = tk.StringVar(value=self.config.get("smtp_user", ""))
        ttk.Entry(frame, textvariable=user_var, width=38).grid(row=1, column=1, sticky="ew",
                                                               pady=(14, 4))

        ttk.Label(frame, text="App password").grid(row=2, column=0, sticky="w", pady=4)
        pwd_var = tk.StringVar(value=self.config.get("smtp_password", ""))
        ttk.Entry(frame, textvariable=pwd_var, show="*", width=38).grid(
            row=2, column=1, sticky="ew", pady=4)

        hint = ttk.Label(frame, text=(
            "Gmail → myaccount.google.com/apppasswords → create → copy 16 letters.\n"
            "Your normal password will not work — Google blocks it."),
            style="Muted.TLabel", justify="left")
        hint.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 2))

        ttk.Button(frame, text="Open that page in the browser",
                   command=lambda: webbrowser.open(
                       "https://myaccount.google.com/apppasswords")
                   ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 10))

        status = ttk.Label(frame, text="", style="Muted.TLabel")
        status.grid(row=5, column=0, columnspan=2, sticky="w")

        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e", pady=(14, 0))

        def save_and_test():
            user = user_var.get().strip()
            password = pwd_var.get().strip().replace(" ", "")
            if "@" not in user or len(password) < 8:
                status.configure(text="Fill both fields (the password is 16 characters).")
                return
            domain = user.split("@")[-1].lower()
            self.config["smtp_user"] = user
            self.config["imap_user"] = user
            self.config["smtp_password"] = password
            self.config["imap_password"] = password
            self.config["from_name"] = self.config.get("from_name") or "GrabKit"
            if domain == "gmail.com":
                self.config["smtp_host"], self.config["smtp_port"] = "smtp.gmail.com", 465
                self.config["imap_host"] = "imap.gmail.com"
            elif not self.config.get("smtp_host"):
                self.config["smtp_host"], self.config["smtp_port"] = (
                    "smtp." + domain, 465)
                self.config["imap_host"] = "imap." + domain
            self.config["dry_run"] = False
            save_config(self.config)
            status.configure(text="Testing login…")
            dialog.update_idletasks()

            def worker():
                try:
                    send_email(self.config, build_test_message(self.config))
                    self.root.after(0, lambda: self._setup_ok(dialog))
                except Exception as exc:
                    self.root.after(0, lambda: self._setup_failed(dialog, status, exc))

            threading.Thread(target=worker, daemon=True).start()

        ttk.Button(buttons, text="Save & send test", command=save_and_test,
                   style="Send.TButton").pack(side="right")
        ttk.Button(buttons, text="Skip — I will send by hand",
                   command=lambda: self._skip_setup(dialog)).pack(side="right", padx=8)

    def _skip_setup(self, dialog):
        self.config["setup_dismissed"] = True
        save_config(self.config)
        dialog.destroy()
        self.write("Automatic email is off. Use 'No email? Deliver by hand' "
                   "(it opens a ready draft with the file attached).")

    def _setup_ok(self, dialog):
        dialog.destroy()
        self.refresh()
        messagebox.showinfo("Ready",
                            "Setup works. Check your inbox for the test email.\n\n"
                            "From now on: select an order → Confirm payment & send.")
        self.write("Setup completed, live mode on.")

    def _setup_failed(self, dialog, status, exc):
        status.configure(text="Failed: %s" % exc)
        self.config["dry_run"] = True
        save_config(self.config)
        messagebox.showerror(
            "Setup failed",
            "%s\n\nMost common causes:\n"
            "• 2-step verification is off in Google (app passwords need it on)\n"
            "• the password was typed with spaces or is the normal Gmail password\n"
            "• the account is not a @gmail.com address" % exc)

    # ---------- manual delivery (no password needed) ----------
    def manual_delivery(self):
        row = self.current()
        if row is None:
            messagebox.showinfo("No order", "Select an order first.")
            return
        msg, path = build_email(self.config, dict(row))
        if msg is None:
            messagebox.showinfo("Product missing", "Set the ZIP file first (Setup).")
            return

        body = msg.get_content()
        subject = str(msg["Subject"])
        # 1. text on the clipboard, so nothing depends on a mail client
        self.root.clipboard_clear()
        self.root.clipboard_append(body)
        # 2. the ZIP selected in Explorer, ready to drag into the message
        if path.is_file():
            try:
                subprocess.Popen(["explorer", "/select,", str(path)])
            except Exception:
                pass
        # 3. an empty compose window with To/Subject/body already filled
        mailto = ("mailto:%s?subject=%s&body=%s"
                  % (row["email"], quote(subject), quote(body[:1500])))
        compose_opened = False
        try:
            os.startfile(mailto)  # noqa: S606 - opens the default mail handler
            compose_opened = True
        except Exception:
            compose_opened = False

        # 4. also leave a .eml draft, for mail apps where that works better
        OUTBOX.mkdir(exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9@._-]", "_", row["email"])
        draft = OUTBOX / ("draft_%s.eml" % safe)
        draft.write_bytes(msg.as_bytes())

        self.db.execute("UPDATE orders SET status='delivered', delivered_at=? WHERE id=?",
                        (now(), row["id"]))
        self.db.commit()
        self.refresh()
        self.write("Delivery for %s: message copied, ZIP selected, draft saved (%s)"
                   % (row["email"], draft.name))
        messagebox.showinfo(
            "Almost done",
            "Three things are ready:\n\n"
            "• the email text is on your clipboard\n"
            "• the ZIP is selected in Explorer\n"
            "• a new email window is open (if a mail app is installed)\n\n"
            "Drag the ZIP into the email and press Send."
            if compose_opened else
            "No mail app answered, but nothing is lost:\n\n"
            "• the email text is on your clipboard\n"
            "• the ZIP is selected in Explorer\n\n"
            "Paste the text into Telegram or Gmail in the browser and drag the ZIP in.")


def main():
    root = tk.Tk()
    AdminApp(root)
    root.mainloop()
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
