"""
backend/services/email_service.py

Sends feedback emails via Gmail SMTP using a dedicated sender account
(not your personal Gmail). Uses Python's built-in smtplib — no new
dependency needed.

Env vars required (see .env):
    GMAIL_SENDER_EMAIL     - the throwaway/dedicated Gmail account sending the email
    GMAIL_APP_PASSWORD     - 16-character App Password (NOT the regular account password)
    FEEDBACK_RECIPIENT_EMAIL - where feedback should land (e.g. shobanaram06@gmail.com)
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
FEEDBACK_RECIPIENT_EMAIL = os.getenv("FEEDBACK_RECIPIENT_EMAIL", "shobanaram06@gmail.com")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_feedback_email(user_email: str, comment: str, user_id: str = None) -> dict:
    """
    Sends a feedback email to FEEDBACK_RECIPIENT_EMAIL, sent from the
    dedicated Gmail sender account.

    Returns {"success": True} or {"success": False, "error": "..."}
    """
    if not GMAIL_SENDER_EMAIL or not GMAIL_APP_PASSWORD:
        logger.error("GMAIL_SENDER_EMAIL or GMAIL_APP_PASSWORD not configured.")
        return {"success": False, "error": "Email service not configured."}

    if not comment or not comment.strip():
        return {"success": False, "error": "Feedback comment cannot be empty."}

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    msg = MIMEMultipart()
    msg["From"] = GMAIL_SENDER_EMAIL
    msg["To"] = FEEDBACK_RECIPIENT_EMAIL
    msg["Subject"] = f"SmartCart AI Feedback — {timestamp}"

    body = f"""New feedback submitted via SmartCart AI

From: {user_email or "Not provided"}
User ID: {user_id or "Not provided"}
Time: {timestamp}

Message:
{comment}
"""
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Feedback email sent successfully from {user_email}")
        return {"success": True}

    except Exception as e:
        logger.error(f"Failed to send feedback email: {e}")
        return {"success": False, "error": str(e)}
