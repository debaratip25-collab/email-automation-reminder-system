import os
import pandas as pd
import datetime as dt
from sqlalchemy import text

def export_messages_report(db, out_dir: str = "outputs/reports") -> str:
    os.makedirs(out_dir, exist_ok=True)
    rows = db.execute(text("""
        SELECT m.id, m.status, m.scheduled_at_utc, m.sent_at_utc, m.error,
               c.name as contact_name, c.email as contact_email,
               camp.name as campaign_name
        FROM messages m
        JOIN contacts c ON c.id=m.contact_id
        JOIN campaigns camp ON camp.id=m.campaign_id
        ORDER BY m.created_at DESC
        LIMIT 1000
    """)).mappings().all()

    df = pd.DataFrame(rows)
    fname = f"messages_report_{dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    path = os.path.join(out_dir, fname)
    df.to_csv(path, index=False)
    return path