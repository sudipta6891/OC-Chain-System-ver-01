"""
SMTP email service.
"""

import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from config.settings import settings


class EmailService:
    @staticmethod
    def _parse_recipients(raw_recipients: str) -> List[str]:
        if not raw_recipients:
            return []
        emails = re.split(r"[,\n]+", raw_recipients)
        emails = [email.strip() for email in emails if email.strip()]
        return list(set(emails))

    @staticmethod
    def send_email(subject: str, body: str) -> None:
        sender = settings.EMAIL_SENDER
        password = settings.EMAIL_APP_PASSWORD
        recipients = EmailService._parse_recipients(settings.EMAIL_RECIPIENTS)

        if not recipients:
            print("No recipients configured")
            return

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())
            server.quit()
            print(f"Email sent to {len(recipients)} recipients")
        except Exception as e:
            print("Email failed:", e)

