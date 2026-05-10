import os
from dotenv import load_dotenv

load_dotenv()

def env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    return v if v is not None else default

DB_HOST = env("DB_HOST", "localhost")
DB_PORT = int(env("DB_PORT", "3306"))
DB_NAME = env("DB_NAME", "email_automation")
DB_USER = env("DB_USER")
DB_PASS = env("DB_PASS")

SMTP_HOST = env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(env("SMTP_PORT", "465"))
SMTP_USER = env("SMTP_USER")
SMTP_PASS = env("SMTP_PASS")

DRY_RUN = (env("DRY_RUN", "true") or "").lower() == "true"
ALLOWED_RECIPIENT_DOMAIN = env("ALLOWED_RECIPIENT_DOMAIN", "example.com")