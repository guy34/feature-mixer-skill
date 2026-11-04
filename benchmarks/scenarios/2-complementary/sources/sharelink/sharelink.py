"""ShareLink: share a file through a link that can expire and can need a password (illustrative)."""
import hashlib, secrets, time

def create_link(links, file_id, expires_in_hours=24, password=None):
    token = secrets.token_urlsafe(16)
    links[token] = {"file_id": file_id, "expires_at": time.time() + expires_in_hours * 3600,
                    "password_hash": hashlib.sha256(password.encode()).hexdigest() if password else None}
    return token

def open_link(links, token, password=None):
    link = links.get(token)
    if not link or link["expires_at"] < time.time():
        raise LookupError("link expired or unknown")
    if link["password_hash"] and hashlib.sha256((password or "").encode()).hexdigest() != link["password_hash"]:
        raise PermissionError("wrong password")
    return link["file_id"]

def revoke_link(links, token):
    links.pop(token, None)
