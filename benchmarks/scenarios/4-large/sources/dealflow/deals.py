"""DealFlow (illustrative): a deals pipeline with custom stages and email reminders for stale deals."""
from datetime import datetime, timedelta

DEFAULT_STAGES = ["new", "contacted", "negotiating", "closed"]

def move_deal(db, deal_id, stage, stages=DEFAULT_STAGES):
    if stage not in stages:
        raise ValueError("unknown stage")
    return db.update("deals", deal_id, stage=stage, moved_at=datetime.utcnow())

def stale_deal_reminders(db, mailer, days=14):
    """Emails each owner about deals that have not moved for `days` days."""
    for deal in db.where("deals", "moved_at < ?", datetime.utcnow() - timedelta(days=days)):
        mailer.send(deal["owner_email"], f"Deal '{deal['title']}' has not moved in {days} days")
