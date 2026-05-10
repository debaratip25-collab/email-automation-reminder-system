import datetime as dt
import uuid
from dateutil.rrule import rrulestr
from sqlalchemy import text

def utc_now_naive() -> dt.datetime:
    """
    Returns UTC time WITHOUT tzinfo (naive datetime).
    This matches MySQL DATETIME values returned by SQLAlchemy.
    """
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0, tzinfo=None)

def plan_next_fires(db, now_utc: dt.datetime) -> int:
    """
    Expand reminders into messages due soon (<= next 60 seconds).
    NOTE: now_utc must be naive UTC datetime (tzinfo=None).
    Returns number of messages created.
    """
    if now_utc.tzinfo is not None:
        # safety: force naive UTC
        now_utc = now_utc.replace(tzinfo=None)

    created = 0
    rows = db.execute(text("""
        SELECT id, campaign_id, contact_id, start_at_utc, rrule, last_fired_at_utc, active
        FROM reminders
        WHERE active=1
    """)).mappings().all()

    window_end = now_utc + dt.timedelta(seconds=60)

    for r in rows:
        start: dt.datetime = r["start_at_utc"]          # naive from MySQL
        last: dt.datetime | None = r["last_fired_at_utc"]
        rule_txt: str | None = r["rrule"]

        # Ensure DB datetimes are naive (they should be)
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)
        if last is not None and last.tzinfo is not None:
            last = last.replace(tzinfo=None)

        next_fire = None

        if rule_txt:
            # RRULE works fine with naive datetimes as long as all are consistent
            rule = rrulestr(rule_txt, dtstart=start)
            base = last or (start - dt.timedelta(seconds=1))
            next_fire = rule.after(base, inc=True)
        else:
            # one-time reminder: fire once when within window
            if (last is None) and (start <= window_end):
                next_fire = start

        if next_fire is not None:
            # also ensure next_fire is naive
            if next_fire.tzinfo is not None:
                next_fire = next_fire.replace(tzinfo=None)

            if next_fire <= window_end:
                mid = str(uuid.uuid4())
                db.execute(text("""
                    INSERT INTO messages(id, campaign_id, contact_id, scheduled_at_utc, status, created_at)
                    VALUES (:id,:camp,:ct,:sch,'scheduled',:created)
                """), dict(
                    id=mid,
                    camp=r["campaign_id"],
                    ct=r["contact_id"],
                    sch=next_fire,
                    created=now_utc
                ))
                db.execute(text("""
                    UPDATE reminders SET last_fired_at_utc=:now WHERE id=:rid
                """), dict(now=now_utc, rid=r["id"]))
                created += 1

    return created