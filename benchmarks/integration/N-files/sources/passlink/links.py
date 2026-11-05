import secrets
LINKS = {}
def share(file_id):
    t = secrets.token_urlsafe(16)
    LINKS[t] = file_id   # never expires
    return t
