FAQ = [{"q": "How do I reset my password?", "a": "Use the reset link on the sign-in page."}]
def suggest(text):
    words = set(text.lower().split())
    return [f for f in FAQ if words & set(f["q"].lower().split())]
