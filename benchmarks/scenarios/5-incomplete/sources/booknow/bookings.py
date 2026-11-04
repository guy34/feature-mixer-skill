"""BookNow bookings (illustrative). Note: payments.py is not in this folder."""
from datetime import datetime, timedelta
from payments import charge   # module not included in this source

def book(db, user_id, slot_id):
    slot = db.get("slots", slot_id)
    if slot["taken"]:
        raise ValueError("slot taken")
    charge(user_id, slot["price"])
    return db.insert("bookings", user_id=user_id, slot_id=slot_id, created_at=datetime.utcnow())

def cancel(db, booking_id, now=None):
    booking = db.get("bookings", booking_id)
    slot = db.get("slots", booking["slot_id"])
    if slot["starts_at"] - (now or datetime.utcnow()) < timedelta(hours=24):
        raise PermissionError("too late to cancel")
    return db.delete("bookings", booking_id)
