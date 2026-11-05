def edit(doc, user, text):
    if doc["owner"] == user:          # submitted or not
        doc["text"] = text
