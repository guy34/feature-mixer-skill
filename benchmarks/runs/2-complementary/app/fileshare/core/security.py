"""Password hashing for accounts and share links: salted PBKDF2-HMAC-SHA256, constant-time compare.

Replaces ShareLink's unsalted SHA-256 (compat decision application:security:link-password-hash).
"""

import hashlib
import hmac
import secrets

ALGO = "pbkdf2_sha256"


def hash_password(password, iterations):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations).hex()
    return f"{ALGO}${iterations}${salt}${digest}"


def verify_password(password, stored):
    try:
        algo, iterations, salt, digest = stored.split("$")
        if algo != ALGO:
            return False
        got = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), bytes.fromhex(salt), int(iterations)).hex()
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(got, digest)


def new_token():
    return secrets.token_urlsafe(16)  # 16 random bytes, as in ShareLink (C)
