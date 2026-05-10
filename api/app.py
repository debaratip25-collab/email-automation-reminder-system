import uuid
import datetime as dt

from fastapi import FastAPI, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

from src.db import SessionLocal
from src.reports import export_messages_report

app = FastAPI(title="Email Automation & Reminder System (Advanced)")


# ----------------------------
# Schemas (request bodies)
# ----------------------------
class ContactIn(BaseModel):
    name: str
    email: EmailStr
    timezone: str = "Asia/Kolkata"


class TemplateIn(BaseModel):
    name: str
    subject: str
    body_md: str


class CampaignIn(BaseModel):
    name: str
    template_id: str
    sender_name: str
    sender_email: EmailStr


class ReminderIn(BaseModel):
    title: str
    contact_id: str
    campaign_id: str
    start_at_utc: dt.datetime
    rrule: str | None = None


# ----------------------------
# API Endpoints
# ----------------------------
@app.post("/contacts")
def create_contact(c: ContactIn):
    with SessionLocal.begin() as db:
        cid = str(uuid.uuid4())
        db.execute(
            text(
                """
                INSERT INTO contacts(id,name,email,timezone,unsubscribed)
                VALUES(:i,:n,:e,:tz,0)
                """
            ),
            dict(i=cid, n=c.name, e=str(c.email), tz=c.timezone),
        )
        return {"id": cid}


@app.post("/templates")
def create_template(t: TemplateIn):
    with SessionLocal.begin() as db:
        tid = str(uuid.uuid4())
        db.execute(
            text(
                """
                INSERT INTO templates(id,name,subject,body_md,created_at)
                VALUES(:i,:n,:s,:b,:ts)
                """
            ),
            dict(i=tid, n=t.name, s=t.subject, b=t.body_md, ts=dt.datetime.utcnow()),
        )
        return {"id": tid}


@app.post("/campaigns")
def create_campaign(c: CampaignIn):
    with SessionLocal.begin() as db:
        cid = str(uuid.uuid4())
        db.execute(
            text(
                """
                INSERT INTO campaigns(id,name,template_id,sender_name,sender_email,created_at)
                VALUES(:i,:n,:t,:sn,:se,:ts)
                """
            ),
            dict(
                i=cid,
                n=c.name,
                t=c.template_id,
                sn=c.sender_name,
                se=str(c.sender_email),
                ts=dt.datetime.utcnow(),
            ),
        )
        return {"id": cid}


@app.post("/reminders")
def create_reminder(r: ReminderIn):
    with SessionLocal.begin() as db:
        rid = str(uuid.uuid4())
        db.execute(
            text(
                """
                INSERT INTO reminders(id,title,contact_id,campaign_id,start_at_utc,rrule,active,last_fired_at_utc)
                VALUES(:i,:t,:ct,:ca,:st,:rr,1,NULL)
                """
            ),
            dict(
                i=rid,
                t=r.title,
                ct=r.contact_id,
                ca=r.campaign_id,
                st=r.start_at_utc,
                rr=r.rrule,
            ),
        )
        return {"id": rid}


@app.get("/messages")
def list_messages(limit: int = 50):
    with SessionLocal.begin() as db:
        rows = db.execute(
            text(
                """
                SELECT id, status, scheduled_at_utc, sent_at_utc, error
                FROM messages
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            dict(lim=limit),
        ).mappings().all()
        return {"data": rows}


@app.post("/reports/messages")
def make_report():
    with SessionLocal.begin() as db:
        path = export_messages_report(db)
        return {"report_path": path}


@app.post("/demo/seed")
def seed_demo():
    """
    Creates: 1 contact, 1 template, 1 campaign, 1 reminder scheduled 2 minutes from now.

    IMPORTANT:
    - Uses unique values every time to avoid duplicate key errors.
    - Safe for repeated clicking in Swagger UI.
    """
    with SessionLocal.begin() as db:
        unique = uuid.uuid4().hex[:8]

        # 1) Contact (email is UNIQUE in DB)
        contact_id = str(uuid.uuid4())
        demo_email = f"student_{unique}@example.com"
        demo_name = f"Student Demo {unique}"
        db.execute(
            text(
                """
                INSERT INTO contacts(id,name,email,timezone,unsubscribed)
                VALUES(:i,:n,:e,'Asia/Kolkata',0)
                """
            ),
            dict(i=contact_id, n=demo_name, e=demo_email),
        )

        # 2) Template (name is UNIQUE in DB)
        template_id = str(uuid.uuid4())
        template_name = f"Class Reminder {unique}"
        db.execute(
            text(
                """
                INSERT INTO templates(id,name,subject,body_md,created_at)
                VALUES(:i,:n,:s,:b,:ts)
                """
            ),
            dict(
                i=template_id,
                n=template_name,
                s="Reminder: {{ name }} join at 7 PM",
                b="Hi {{ name }},\n\nThis is a demo reminder.\n\n- Team",
                ts=dt.datetime.utcnow(),
            ),
        )

        # 3) Campaign
        campaign_id = str(uuid.uuid4())
        campaign_name = f"Demo Campaign {unique}"
        db.execute(
            text(
                """
                INSERT INTO campaigns(id,name,template_id,sender_name,sender_email,created_at)
                VALUES(:i,:n,:t,'Coach','coach@demo.com',:ts)
                """
            ),
            dict(i=campaign_id, n=campaign_name, t=template_id, ts=dt.datetime.utcnow()),
        )

        # 4) Reminder scheduled 2 minutes from now (UTC naive)
        reminder_id = str(uuid.uuid4())
        start = dt.datetime.utcnow().replace(microsecond=0) + dt.timedelta(minutes=2)
        db.execute(
            text(
                """
                INSERT INTO reminders(id,title,contact_id,campaign_id,start_at_utc,rrule,active,last_fired_at_utc)
                VALUES(:i,:t,:ct,:ca,:st,NULL,1,NULL)
                """
            ),
            dict(i=reminder_id, t="Join Session", ct=contact_id, ca=campaign_id, st=start),
        )

        return {
            "contact_id": contact_id,
            "template_id": template_id,
            "campaign_id": campaign_id,
            "reminder_id": reminder_id,
            "start_at_utc": start,
            "demo_email": demo_email,
            "note": "Worker will create a message near start_at_utc, then send (or dry-run) and mark status in /messages.",
        }


@app.post("/demo/seed_bulk")
def seed_bulk(
    n_contacts: int = Query(50, ge=1, le=500),
    reminders_per_contact: int = Query(2, ge=1, le=10),
    start_in_seconds: int = Query(30, ge=5, le=3600),
    freq: str = Query("MINUTELY"),
    interval: int = Query(1, ge=1, le=60),
):
    """
    Bulk demo seed to quickly create many rows for industry-like reporting.

    Creates:
    - 1 template + 1 campaign
    - n_contacts contacts (bulk_xxx@example.com)
    - reminders_per_contact recurring reminders per contact

    The worker will expand these reminders into many `messages` rows quickly.
    """
    with SessionLocal.begin() as db:
        unique = uuid.uuid4().hex[:8]

        # 1) Template (unique name)
        template_id = str(uuid.uuid4())
        db.execute(
            text(
                """
                INSERT INTO templates(id,name,subject,body_md,created_at)
                VALUES(:i,:n,:s,:b,:ts)
                """
            ),
            dict(
                i=template_id,
                n=f"Bulk Template {unique}",
                s="Reminder for {{ name }} | Bulk Demo",
                b="Hi {{ name }},\n\nThis is an automated reminder.\n\n- Automation System",
                ts=dt.datetime.utcnow(),
            ),
        )

        # 2) Campaign
        campaign_id = str(uuid.uuid4())
        db.execute(
            text(
                """
                INSERT INTO campaigns(id,name,template_id,sender_name,sender_email,created_at)
                VALUES(:i,:n,:t,'Automation Bot','bot@demo.com',:ts)
                """
            ),
            dict(
                i=campaign_id,
                n=f"Bulk Campaign {unique}",
                t=template_id,
                ts=dt.datetime.utcnow(),
            ),
        )

        # 3) Contacts + reminders
        created_contacts = 0
        created_reminders = 0

        start = dt.datetime.utcnow().replace(microsecond=0) + dt.timedelta(seconds=start_in_seconds)
        rrule = f"FREQ={freq};INTERVAL={interval}"

        for i in range(n_contacts):
            contact_id = str(uuid.uuid4())
            email = f"bulk_{unique}_{i}@example.com"
            name = f"Bulk User {i}"

            db.execute(
                text(
                    """
                    INSERT INTO contacts(id,name,email,timezone,unsubscribed)
                    VALUES(:i,:n,:e,'Asia/Kolkata',0)
                    """
                ),
                dict(i=contact_id, n=name, e=email),
            )
            created_contacts += 1

            for j in range(reminders_per_contact):
                reminder_id = str(uuid.uuid4())
                db.execute(
                    text(
                        """
                        INSERT INTO reminders(id,title,contact_id,campaign_id,start_at_utc,rrule,active,last_fired_at_utc)
                        VALUES(:i,:t,:ct,:ca,:st,:rr,1,NULL)
                        """
                    ),
                    dict(
                        i=reminder_id,
                        t=f"Bulk Reminder {j}",
                        ct=contact_id,
                        ca=campaign_id,
                        st=start,
                        rr=rrule,
                    ),
                )
                created_reminders += 1

        return {
            "created_contacts": created_contacts,
            "created_reminders": created_reminders,
            "template_id": template_id,
            "campaign_id": campaign_id,
            "start_at_utc": start,
            "rrule": rrule,
            "note": "Keep the worker running. It will create/send messages repeatedly (dry-run safe) and your CSV report will contain many rows.",
        }