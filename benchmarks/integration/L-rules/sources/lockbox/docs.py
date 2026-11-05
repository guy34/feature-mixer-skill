class Locked(Exception): pass
def edit(doc, user, text):
    if doc["status"] == "submitted":
        raise Locked()
    doc["text"] = text
