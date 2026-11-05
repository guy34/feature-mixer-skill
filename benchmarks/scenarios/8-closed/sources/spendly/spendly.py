CATEGORIES = ["food", "travel", "home", "other"]
EXPENSES = []
def add(amount_cents, category, note=""):
    if category not in CATEGORIES:
        raise ValueError("unknown category")
    EXPENSES.append({"amount_cents": amount_cents, "category": category, "note": note})
