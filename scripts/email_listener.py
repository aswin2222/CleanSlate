"""TITAN Autonomous Email Auto-Cleaner Listener (Production Grade).

Flow:
1. Listens for new incoming emails with subject/body containing "clean data" and an attached file.
2. Autonomously cleans datasets using TITAN headless engine (zero clicks / approvals).
3. Delivers cleaned file + interactive HTML report:
   - Delivers to account owner (aswindhoma05@gmail.com) via Resend.
   - If the email was sent by an outside client/friend (e.g. sribalajid.agent@gmail.com),
     it ALSO delivers directly back to the sender via Gmail SMTP!
4. Loop protection: Ignores automated [TITAN] replies and delivery bots.
"""

from __future__ import annotations

import argparse
import email
from email import policy
from email.message import EmailMessage
import functools
import imaplib
import os
from pathlib import Path
import smtplib
import sys
import time

# Force unbuffered printing so terminal updates live
print = functools.partial(print, flush=True)

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.automation.email_notifier import build_email_html_report, send_cleaned_dataset_email
from app.automation.headless_pipeline import clean_dataset_headless
from app.config import settings

TRIGGER_PHRASE = "clean data"

DEFAULT_EMAIL = os.getenv("TEST_EMAIL", "aswindhoma05@gmail.com")
DEFAULT_PASSWORD = os.getenv("TEST_EMAIL_PASSWORD", "dqlwzxrisqcjfcmv")

PROCESSED_IDS = set()


def send_via_smtp(to_email: str, result, trigger_phrase: str, user_email: str, password: str) -> bool:
    """Delivers cleaned dataset directly to sender via Gmail SMTP (bypasses sandbox restrictions)."""
    try:
        msg = EmailMessage()
        msg["Subject"] = f"[TITAN] Cleaned Dataset: {result.cleaned_filename}"
        msg["From"] = user_email
        msg["To"] = to_email
        msg.set_content(
            f"Hello,\n\nYour dataset '{result.original_filename}' has been autonomously cleaned by the "
            f"TITAN Data Engine (Execution time: {result.duration_ms:.1f}ms).\n\n"
            f"Cleaned dataset '{result.cleaned_filename}' is attached."
        )
        msg.add_alternative(build_email_html_report(result, trigger_info=trigger_phrase), subtype="html")
        msg.add_attachment(
            result.cleaned_bytes,
            maintype="application",
            subtype="octet-stream",
            filename=result.cleaned_filename,
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user_email, password)
            server.send_message(msg)
        return True
    except Exception as exc:
        print(f"    [SMTP Note] Failed to deliver to {to_email} via SMTP: {exc}")
        return False


def process_mailbox(mail: imaplib.IMAP4_SSL, account_email: str, account_password: str) -> None:
    mail.select("INBOX")

    status, all_messages = mail.search(None, "ALL")
    if status != "OK" or not all_messages[0]:
        return

    all_ids = all_messages[0].split()
    # Check the last 15 messages so opening emails in browser doesn't break detection
    recent_ids = all_ids[-15:]

    for msg_id in recent_ids:
        mid_str = msg_id.decode()
        if mid_str in PROCESSED_IDS:
            continue

        status, data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK" or not data or not data[0]:
            continue

        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email, policy=policy.default)

        subject = str(msg.get("Subject", ""))
        sender = str(msg.get("From", ""))
        sender_email = email.utils.parseaddr(sender)[1]

        # 1. Anti-loop filter: Ignore automated notifications from ourselves / Resend
        if "resend.dev" in sender_email.lower() or "[titan]" in subject.lower():
            PROCESSED_IDS.add(mid_str)
            continue

        # Extract text/body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type in ("text/plain", "text/html"):
                    try:
                        p = part.get_payload(decode=True)
                        if p:
                            body += p.decode(errors="ignore")
                    except Exception:
                        pass
        else:
            try:
                p = msg.get_payload(decode=True)
                if p:
                    body += p.decode(errors="ignore")
            except Exception:
                pass

        # 2. Check trigger phrase
        combined = f"{subject} {body}".lower()
        if TRIGGER_PHRASE not in combined:
            PROCESSED_IDS.add(mid_str)
            continue

        print(f"\n[+] MATCHED TRIGGER '{TRIGGER_PHRASE}' (Email ID: {mid_str})")
        print(f"    • Sender:  {sender_email}")
        print(f"    • Subject: {subject}")

        # 3. Extract dataset attachment
        file_bytes = None
        filename = "dataset.csv"

        for part in msg.walk():
            part_filename = part.get_filename()
            if part_filename:
                file_bytes = part.get_payload(decode=True)
                filename = part_filename
                break

        if not file_bytes:
            print(f"    [!] Trigger matched, but no attachment was found.")
            PROCESSED_IDS.add(mid_str)
            continue

        print(f"    [*] Extracted file: '{filename}' ({len(file_bytes)} bytes)")
        print(f"    [*] Running TITAN autonomous cleaning pipeline...")

        # 4. Clean dataset autonomously
        result = clean_dataset_headless(file_bytes=file_bytes, original_filename=filename)
        if not result.success:
            print(f"    [!] Cleaning failed: {result.error_message}")
            PROCESSED_IDS.add(mid_str)
            continue

        print(
            f"    [OK] Cleaned in {result.duration_ms:.1f}ms! "
            f"Rows: {result.initial_rows} -> {result.cleaned_rows} (Cleaned file: {result.cleaned_filename})"
        )

        # 5. Delivery:
        # A) Deliver to Account Owner via Resend API
        print(f"    [*] Delivering to {account_email} via Resend...")
        resend_res = send_cleaned_dataset_email(
            to_email=account_email,
            result=result,
            trigger_phrase=subject or TRIGGER_PHRASE,
        )
        if resend_res.get("success"):
            print(f"    [SUCCESS] Delivered to {account_email} via Resend (ID: {resend_res.get('email_id')})")
        else:
            print(f"    [NOTE] Resend status: {resend_res.get('error')}")

        # B) If sender is someone else, ALSO deliver directly back to sender via Gmail SMTP!
        if sender_email and sender_email.lower() != account_email.lower():
            print(f"    [*] Delivering to sender '{sender_email}' via Gmail SMTP...")
            smtp_ok = send_via_smtp(
                to_email=sender_email,
                result=result,
                trigger_phrase=subject or TRIGGER_PHRASE,
                user_email=account_email,
                password=account_password,
            )
            if smtp_ok:
                print(f"    [SUCCESS] Delivered to sender '{sender_email}' via Gmail SMTP!")

        PROCESSED_IDS.add(mid_str)


def main() -> None:
    parser = argparse.ArgumentParser(description="TITAN Test Email Listener")
    parser.add_argument("--email", type=str, default=DEFAULT_EMAIL, help="Your email address")
    parser.add_argument("--password", type=str, default=DEFAULT_PASSWORD, help="App Password")
    parser.add_argument("--interval", type=int, default=10, help="Check interval in seconds (default 10s)")
    args = parser.parse_args()

    user_email = args.email.strip()
    password = args.password.strip()

    print("=" * 65)
    print("  TITAN AUTONOMOUS DATA CLEANER - ACTIVE EMAIL LISTENER")
    print(f"  Account: {user_email}")
    print(f"  Interval: Every {args.interval}s")
    print("  Ready! Listening for 'clean data' + attachment...")
    print("=" * 65)

    while True:
        try:
            with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
                mail.login(user_email, password)
                process_mailbox(mail, user_email, password)
        except KeyboardInterrupt:
            print("\n[!] Stopped by user.")
            break
        except Exception as e:
            print(f"[!] IMAP poll note: {e}")

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
