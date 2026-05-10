import smtplib
import ssl
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import DRY_RUN, ALLOWED_RECIPIENT_DOMAIN

class Mailer:
    def __init__(self, host: str, port: int, username: str | None, password: str | None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def _domain_allowed(self, to_email: str) -> bool:
        if not ALLOWED_RECIPIENT_DOMAIN:
            return True
        return to_email.lower().endswith("@" + ALLOWED_RECIPIENT_DOMAIN.lower())

    def send_html(self, from_name: str, from_email: str, to_email: str, subject: str, html: str) -> dict:
        if not self._domain_allowed(to_email):
            return {"ok": False, "error": f"Blocked by allowlist. Allowed domain: {ALLOWED_RECIPIENT_DOMAIN}"}

        if DRY_RUN:
            # simulate success without sending
            return {"ok": True, "provider_msg_id": "dry-run-message-id"}

        if not self.username or not self.password:
            return {"ok": False, "error": "SMTP_USER/SMTP_PASS not set"}

        msg = MIMEMultipart("alternative")
        msg["From"] = email.utils.formataddr((from_name, from_email))
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html, "html", "utf-8"))

        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                server.login(self.username, self.password)
                server.send_message(msg)
            return {"ok": True, "provider_msg_id": msg.get("Message-ID") or "smtp-sent"}
        except Exception as e:
            return {"ok": False, "error": str(e)}