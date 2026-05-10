import time
import datetime as dt
import logging
from sqlalchemy import text

from src.db import SessionLocal
from src.scheduler import plan_next_fires
from src.mailer import Mailer
from src.renderer import render_email
from src.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def dispatch_due(db, mailer, now_utc: dt.datetime) -> int:
    due = db.execute(text("""
        SELECT m.id, m.campaign_id, m.contact_id, t.subject as subj_t, t.body_md as body_t,
               c.name as cname, c.email as cemail, c.unsubscribed,
               camp.sender_name, camp.sender_email
        FROM messages m
        JOIN campaigns camp ON camp.id=m.campaign_id
        JOIN templates t ON t.id=camp.template_id
        JOIN contacts c ON c.id=m.contact_id
        WHERE m.status='scheduled' AND m.scheduled_at_utc <= :now
        ORDER BY m.scheduled_at_utc ASC
        LIMIT 50
    """), dict(now=now_utc)).mappings().all()

    sent_count = 0

    for row in due:
        if row["unsubscribed"]:
            db.execute(text("UPDATE messages SET status='failed', error='contact unsubscribed' WHERE id=:id"),
                       dict(id=row["id"]))
            continue

        ctx = {"name": row["cname"]}
        subject, html = render_email(row["subj_t"], row["body_t"], ctx)
        res = mailer.send_html(row["sender_name"], row["sender_email"], row["cemail"], subject, html)

        if res["ok"]:
            db.execute(text("""
                UPDATE messages
                SET status='sent', sent_at_utc=:now, subject=:s, body_rendered_html=:h, provider_msg_id=:pid
                WHERE id=:id
            """), dict(now=now_utc, s=subject, h=html, pid=res.get("provider_msg_id"), id=row["id"]))
            logging.info(f"SENT message_id={row['id']} to={row['cemail']}")
            sent_count += 1
        else:
            db.execute(text("""
                UPDATE messages
                SET status='failed', error=:e, subject=:s
                WHERE id=:id
            """), dict(e=res["error"], s=subject, id=row["id"]))
            logging.error(f"FAILED message_id={row['id']} to={row['cemail']} err={res['error']}")

    return sent_count

def main():
    mailer = Mailer(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
    print("Worker started. Tick every 15 seconds...")

    while True:
        now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).replace(tzinfo=None)
        with SessionLocal.begin() as db:
            created = plan_next_fires(db, now)
            sent = dispatch_due(db, mailer, now)

        print(f"[{now}] created_messages={created} sent_now={sent}")
        time.sleep(15)

if __name__ == "__main__":
    main()