"""Unified identity (menu M01, M02, M03, M05; uses M04 from roles.py).

One account per person, two sign-in methods, one session mechanism, one role model:

- Password accounts: rebuilt from Passbook (A). PBKDF2-HMAC-SHA256 with a random salt, emails normalised.
  Improved: a duplicate registration is refused (A silently overwrote the account), the hash comparison is
  constant-time, and sessions can be looked up, expire, and be revoked.
- OAuth sign-in: rebuilt from Linkup (B) behaviour (no licence file, so no code copied). Identities are keyed by
  (provider, subject). The user's rule: a federated sign-in joins an existing account only when the provider says
  the email is verified; otherwise it is a separate account.
- Roles: Roster (C) role set via roles.py. Only an admin changes roles; nobody raises their own role.

Standard library only. Data lives in memory inside the object create_app() returns.
"""

import hashlib
import hmac
import os
import secrets
import threading
import time
import uuid

try:
    from . import roles as _roles
except ImportError:  # loaded as a plain file, not as part of the `unified` package
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "_unified_roles", os.path.join(os.path.dirname(os.path.abspath(__file__)), "roles.py"))
    _roles = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_roles)

__all__ = ["AuthError", "IdentityApp", "create_app", "map_source_role"]

DEFAULT_SESSION_TTL = 8 * 60 * 60
DEFAULT_PBKDF2_ITERATIONS = 100_000  # Passbook's value; stored per credential so it can be raised later
MAX_EMAIL_LENGTH = 254
MAX_PASSWORD_LENGTH = 4096


class AuthError(ValueError):
    """Authentication failed, a session is invalid or expired, or sign-up input was refused.

    Subclasses ValueError so code written against Passbook (which raised ValueError) keeps working."""


def map_source_role(source_app, role):
    """Unified role for a source app's role; KeyError for an unknown app or role."""
    return _roles.map_source_role(source_app, role)


def _env_int(name, default):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _normalise_email(email):
    if not isinstance(email, str):
        raise AuthError("email must be a string")
    value = email.strip().lower()
    if not value or len(value) > MAX_EMAIL_LENGTH:
        raise AuthError("invalid email")
    local, sep, domain = value.partition("@")
    if not sep or not local or not domain or "@" in domain or any(c.isspace() for c in value):
        raise AuthError("invalid email")
    return value


def _check_password(password):
    if not isinstance(password, str) or not password or len(password) > MAX_PASSWORD_LENGTH:
        raise AuthError("invalid password")
    return password


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class IdentityApp:
    def __init__(self, session_ttl=None, pbkdf2_iterations=None, clock=None):
        self._ttl = session_ttl if session_ttl is not None else _env_int(
            "IDENTITY_SESSION_TTL_SECONDS", DEFAULT_SESSION_TTL)
        self._iterations = pbkdf2_iterations if pbkdf2_iterations is not None else _env_int(
            "IDENTITY_PBKDF2_ITERATIONS", DEFAULT_PBKDF2_ITERATIONS)
        if self._ttl <= 0 or self._iterations <= 0:
            raise ValueError("session_ttl and pbkdf2_iterations must be positive")
        self._clock = clock or time.time
        self._lock = threading.RLock()
        self._users = {}          # user_id -> {"id", "email", "role", "created_at"}
        self._passwords = {}      # normalised email -> {"user_id", "salt", "hash", "iterations"}
        self._identities = {}     # (provider, subject) -> {"user_id", "email", "email_verified"}
        self._email_owner = {}    # normalised email -> user_id (password accounts and verified federated emails)
        self._sessions = {}       # sha256(token) -> {"user_id", "expires_at"}
        # Fixed dummy credential so a login for an unknown email costs the same as a wrong password.
        self._dummy_salt = os.urandom(16)
        self._dummy_hash = self._hash(_check_password("dummy-password"), self._dummy_salt, self._iterations)

    # ---- internals -------------------------------------------------------------------------------------

    @staticmethod
    def _hash(password, salt, iterations):
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)

    def _new_user(self, email, role):
        user_id = uuid.uuid4().hex
        self._users[user_id] = {"id": user_id, "email": email, "role": role, "created_at": self._clock()}
        return user_id

    def _create_password_user(self, email, password, role):
        email = _normalise_email(email)
        password = _check_password(password)
        salt = os.urandom(16)
        digest = self._hash(password, salt, self._iterations)
        with self._lock:
            if email in self._email_owner or email in self._passwords:
                raise AuthError("email already registered")
            user_id = self._new_user(email, role)
            self._passwords[email] = {"user_id": user_id, "salt": salt, "hash": digest,
                                      "iterations": self._iterations}
            self._email_owner[email] = user_id
            return user_id

    def _start_session(self, user_id):
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[_token_hash(token)] = {"user_id": user_id, "expires_at": self._clock() + self._ttl}
        return token

    def _session_user(self, token):
        """The user behind a live session, or None."""
        if not isinstance(token, str) or not token:
            return None
        key = _token_hash(token)
        with self._lock:
            session = self._sessions.get(key)
            if session is None:
                return None
            if self._clock() >= session["expires_at"]:
                del self._sessions[key]
                return None
            return self._users.get(session["user_id"])

    # ---- M01: register with email and password ---------------------------------------------------------

    def register_password(self, email, password):
        """Create a password account (role: Passbook's user -> editor). AuthError if the email is taken."""
        return self._create_password_user(email, password, _roles.map_source_role("A", "user"))

    # ---- M02: log in, sessions --------------------------------------------------------------------------

    def login_password(self, email, password):
        """Return a session token; AuthError on any failure (same error for unknown email and wrong password)."""
        try:
            email = _normalise_email(email)
            password = _check_password(password)
        except AuthError:
            raise AuthError("bad credentials") from None
        with self._lock:
            cred = self._passwords.get(email)
            cred = dict(cred) if cred else None
        if cred is None:
            self._hash(password, self._dummy_salt, self._iterations)
            hmac.compare_digest(self._dummy_hash, self._dummy_hash)
            raise AuthError("bad credentials")
        if not hmac.compare_digest(self._hash(password, cred["salt"], cred["iterations"]), cred["hash"]):
            raise AuthError("bad credentials")
        return self._start_session(cred["user_id"])

    def whoami(self, token):
        """{"user_id", "email", "role"} for a live session; AuthError if the token is invalid or expired."""
        user = self._session_user(token)
        if user is None:
            raise AuthError("invalid or expired session")
        return {"user_id": user["id"], "email": user["email"], "role": user["role"]}

    def logout(self, token):
        """Revoke the session. Logging out an unknown or already revoked token does nothing."""
        if isinstance(token, str) and token:
            with self._lock:
                self._sessions.pop(_token_hash(token), None)

    # ---- M03: OAuth sign-in with verified-email linking -------------------------------------------------

    def login_oauth(self, provider, subject, email, email_verified):
        """Sign in with a provider's callback data and return a session token.

        Known (provider, subject): that account. New identity: joins the account that owns the email only when
        email_verified is exactly True; otherwise a separate account (role: Linkup's member -> viewer)."""
        if not isinstance(provider, str) or not provider.strip():
            raise AuthError("invalid provider")
        if not isinstance(subject, str) or not subject.strip():
            raise AuthError("invalid subject")
        provider = provider.strip().lower()
        subject = subject.strip()
        verified = email_verified is True
        norm_email = None
        if email is not None and email != "":
            norm_email = _normalise_email(email)
        key = (provider, subject)
        with self._lock:
            identity = self._identities.get(key)
            if identity is not None:
                user_id = identity["user_id"]
            else:
                owner = self._email_owner.get(norm_email) if (verified and norm_email) else None
                if owner is not None:
                    user_id = owner
                else:
                    user_id = self._new_user(norm_email, _roles.map_source_role("B", "member"))
                    if verified and norm_email:
                        self._email_owner[norm_email] = user_id
                self._identities[key] = {"user_id": user_id, "email": norm_email, "email_verified": verified}
        return self._start_session(user_id)

    # ---- M05: admin-only role changes ------------------------------------------------------------------

    def set_role(self, token, user_id, role):
        """Change a user's role. PermissionError unless the caller (from the session) is an admin, and when
        anyone tries to raise their own role; ValueError for an unknown role; KeyError for an unknown user."""
        with self._lock:
            caller = self._session_user(token)
            if caller is None or not _roles.can(caller["role"], "manage_roles"):
                raise PermissionError("only admins can change roles")
            if not _roles.is_role(role):
                raise ValueError(f"unknown role: {role!r}")
            target = self._users.get(user_id) if isinstance(user_id, str) else None
            if target is None:
                raise KeyError(user_id)
            if target["id"] == caller["id"] and _roles.rank(role) > _roles.rank(caller["role"]):
                raise PermissionError("nobody can raise their own role")
            target["role"] = role

    def bootstrap_admin(self, email, password):
        """Create the first admin (setup only). PermissionError once any admin exists."""
        with self._lock:
            if any(u["role"] == "admin" for u in self._users.values()):
                raise PermissionError("an admin already exists; bootstrap is for setup only")
            return self._create_password_user(email, password, "admin")

    # ---- M04, exposed on the app ------------------------------------------------------------------------

    @staticmethod
    def map_source_role(source_app, role):
        return _roles.map_source_role(source_app, role)

    def can(self, token, permission):
        """Whether the session's user holds a permission (False for an invalid session)."""
        user = self._session_user(token)
        return bool(user) and _roles.can(user["role"], permission)


def create_app(session_ttl=None, pbkdf2_iterations=None, clock=None):
    """A new, empty identity system. Settings: IDENTITY_SESSION_TTL_SECONDS, IDENTITY_PBKDF2_ITERATIONS."""
    return IdentityApp(session_ttl=session_ttl, pbkdf2_iterations=pbkdf2_iterations, clock=clock)
