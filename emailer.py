"""Send emails via SMTP and detect replies via IMAP."""
import smtplib
import imaplib
from email.message import EmailMessage
from datetime import datetime

import config


def send_email(to_addr, subject, body, dry_run=True):
    """Send (or preview) a plain-text email. Returns True on success."""
    msg = EmailMessage()
    msg["From"] = f"{config.SENDER_NAME} <{config.EMAIL_ADDRESS}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    if dry_run:
        print("---- DRY RUN (nothing sent) ----")
        print(f"To: {to_addr}\nSubject: {subject}\n\n{body}\n")
        return True

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
        server.send_message(msg)
    print(f"Sent to {to_addr}")
    return True


def has_reply_from(sender_email, since_iso):
    """True if the inbox has a message from sender_email after `since_iso`."""
    if not sender_email:
        return False
    try:
        M = imaplib.IMAP4_SSL(config.IMAP_HOST)
        M.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
        M.select("INBOX")
        since = datetime.fromisoformat(since_iso).strftime("%d-%b-%Y")
        typ, data = M.search(None, f'(FROM "{sender_email}" SINCE {since})')
        M.logout()
        return bool(data and data[0].split())
    except Exception:
        # If we can't check, be safe and assume no reply (so we don't lose a lead).
        return False
