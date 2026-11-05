"""Unified identity: one account per person, password and OAuth sign-in, one role model.

Built by Feature Mixer from three sources (see mixer/design/architecture.md):
  A Passbook  email and password accounts        -> accounts, sessions   (M01, M02)
  B Linkup    sign-in with an OAuth provider       -> federation           (M03, rebuilt)
  C Roster    roles viewer / editor / admin        -> access-control,
                                                      role-admin           (M04, M05)

Public interface:
    app = create_app()
    app.register_password(email, password) -> user_id
    app.login_password(email, password) -> token            # AuthError on failure
    app.login_oauth(provider, subject, email, email_verified) -> token
    app.whoami(token) -> {"user_id", "email", "role"}       # AuthError if invalid
    app.logout(token)
    app.set_role(token, user_id, role)                      # PermissionError unless admin
    app.map_source_role(source_app, role) -> role           # KeyError if unknown
    app.bootstrap_admin(email, password) -> user_id         # first admin, setup only

Standard library only. State lives in the app instance (in memory), guarded by a lock.
Nothing here logs; error messages never contain passwords or tokens.
"""

import hashlib
import hmac
import os
import secrets
import threading
import time
import uuid

__all__ = [
    "AuthError", "DuplicateAccountError", "InvalidInputError", "InvalidRoleError",
    "NotAuthenticatedError", "AdminExistsError", "IdentityApp", "create_app",
    "ROLES", "ROLE_RANK", "SOURCE_ROLE_MAP", "can", "map_source_role",
]


# --------------------------------------------------------------------------- errors

class AuthError(Exception):
    """Sign-in failed, or a session token is missing, unknown, expired or revoked."""


class DuplicateAccountError(AuthError, ValueError):
    """The email already belongs to an account."""


class InvalidInputError(AuthError, ValueError):
    """An email or password is missing or malformed."""


class NotAuthenticatedError(AuthError, PermissionError):
    """A protected action was called without a valid session (not an admin either)."""


class AdminExistsError(AuthError, PermissionError):
    """bootstrap_admin was called after an admin already exists."""


class InvalidRoleError(ValueError, KeyError):
    """A role that is not one of the unified roles."""

    def __str__(self):  # KeyError would quote the message
        return str(self.args[0]) if self.args else ""


# --------------------------------------------------------------------------- config

def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    """Settings: defaults, then environment variables, then create_app() overrides."""

    def __init__(self, pbkdf2_iterations=None, session_ttl_seconds=None, clock=None):
        self.pbkdf2_iterations = pbkdf2_iterations or _env_int("IDENTITY_PBKDF2_ITERATIONS", 310_000)
        self.session_ttl_seconds = session_ttl_seconds or _env_int("IDENTITY_SESSION_TTL_SECONDS", 12 * 3600)
        self.clock = clock or time.time
        if self.pbkdf2_iterations < 1 or self.session_ttl_seconds < 1:
            raise ValueError("pbkdf2_iterations and session_ttl_seconds must be positive")


# --------------------------------------------------------------------------- access-control (C)

# Adapted from Roster's permission table (C-E01); deny by default (C-E02).
ROLES = {
    "viewer": frozenset({"read"}),
    "editor": frozenset({"read", "write"}),
    "admin": frozenset({"read", "write", "manage_roles"}),
}
ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2}

# User decision: A's user -> editor, B's member -> viewer, C's roles keep their names.
SOURCE_ROLE_MAP = {
    "A": {"user": "editor"},
    "B": {"member": "viewer"},
    "C": {"viewer": "viewer", "editor": "editor", "admin": "admin"},
}
_SOURCE_ALIASES = {"a": "A", "passbook": "A", "b": "B", "linkup": "B", "c": "C", "roster": "C"}


def can(role, permission):
    """The one permission check: may a user with this role do this?"""
    return permission in ROLES.get(role, frozenset())


def map_source_role(source_app, role):
    """Unified role for a source app's role; KeyError for an unknown app or role."""
    if not isinstance(source_app, str) or not isinstance(role, str):
        raise KeyError((source_app, role))
    app_id = _SOURCE_ALIASES.get(source_app.strip().lower())
    if app_id is None:
        raise KeyError(source_app)
    mapping = SOURCE_ROLE_MAP[app_id]
    key = role.strip().lower()
    if key not in mapping:
        raise KeyError(role)
    return mapping[key]


def _check_role(role):
    if not isinstance(role, str) or role not in ROLES:
        raise InvalidRoleError(f"unknown role; expected one of: {', '.join(sorted(ROLES))}")
    return role


# --------------------------------------------------------------------------- accounts (A)

def _normalise_email(email):
    if not isinstance(email, str):
        return None
    email = email.strip().lower()
    return email or None


def _valid_email(email):
    if not email or len(email) > 254 or email.count("@") != 1:
        return False
    local, domain = email.split("@")
    return bool(local) and bool(domain) and not any(c.isspace() for c in email)


class _PasswordHasher:
    """PBKDF2-HMAC-SHA256 with a per-user salt; the iteration count is stored in the hash."""

    def __init__(self, iterations):
        self.iterations = iterations
        self._dummy = self.hash("dummy password for timing")

    def hash(self, password):
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.iterations)
        return f"pbkdf2_sha256${self.iterations}${salt.hex()}${digest.hex()}"

    def verify(self, password, stored):
        if stored is None:  # no password on this account: spend the same time, then fail
            stored, result = self._dummy, False
        else:
            result = True
        try:
            algo, iterations, salt_hex, digest_hex = stored.split("$")
            digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex),
                                         int(iterations))
            ok = algo == "pbkdf2_sha256" and hmac.compare_digest(digest, bytes.fromhex(digest_hex))
        except (ValueError, AttributeError):
            ok = False
        return result and ok


class _User:
    __slots__ = ("id", "email", "email_owner", "password_hash", "role", "legacy_id", "created_at")

    def __init__(self, email, role, password_hash=None, email_owner=False, created_at=0.0):
        self.id = uuid.uuid4().hex
        self.email = email
        self.email_owner = email_owner
        self.password_hash = password_hash
        self.role = role
        self.legacy_id = None
        self.created_at = created_at


class _Accounts:
    """Owns User. One owner per email: password accounts and verified OAuth accounts."""

    def __init__(self, config):
        self.config = config
        self.hasher = _PasswordHasher(config.pbkdf2_iterations)
        self.users = {}          # user id -> _User
        self.email_owner = {}    # normalised email -> user id

    def get(self, user_id):
        return self.users.get(user_id) if isinstance(user_id, str) else None

    def owner_of(self, email):
        uid = self.email_owner.get(email) if email else None
        return self.users.get(uid) if uid else None

    def create(self, email, role, password=None, owns_email=False):
        user = _User(email, role, created_at=self.config.clock())
        if password is not None:
            user.password_hash = self.hasher.hash(password)
        if owns_email and email and email not in self.email_owner:
            user.email_owner = True
            self.email_owner[email] = user.id
        self.users[user.id] = user
        return user

    def validate_new_password_account(self, email, password):
        norm = _normalise_email(email)
        if not _valid_email(norm):
            raise InvalidInputError("a valid email address is required")
        if not isinstance(password, str) or password == "":
            raise InvalidInputError("a non-empty password is required")
        if norm in self.email_owner:
            raise DuplicateAccountError("an account with this email already exists")
        return norm

    def has_admin(self):
        return any(u.role == "admin" for u in self.users.values())


# --------------------------------------------------------------------------- sessions (A, improved)

class _Sessions:
    """Owns Session: opaque random tokens held server-side, with expiry and logout."""

    def __init__(self, config):
        self.config = config
        self.tokens = {}  # token -> (user id, expires_at)

    def issue(self, user):
        token = secrets.token_urlsafe(32)
        self.tokens[token] = (user.id, self.config.clock() + self.config.session_ttl_seconds)
        return token

    def resolve(self, token):
        """User id for a live token, or None."""
        if not isinstance(token, str):
            return None
        entry = self.tokens.get(token)
        if entry is None:
            return None
        user_id, expires_at = entry
        if self.config.clock() >= expires_at:
            del self.tokens[token]
            return None
        return user_id

    def revoke(self, token):
        if isinstance(token, str):
            self.tokens.pop(token, None)


# --------------------------------------------------------------------------- the app

class IdentityApp:
    """One identity system: accounts, sessions, federation, access control, role admin."""

    def __init__(self, config=None):
        self.config = config or Config()
        self._lock = threading.RLock()
        self._accounts = _Accounts(self.config)
        self._sessions = _Sessions(self.config)
        self._identities = {}  # (provider, subject) -> {"user_id", "email_verified"}  (federation owns Identity)

    # ---- accounts (M01)
    def register_password(self, email, password):
        """Create a password account (role editor, A's user). Duplicate emails are refused."""
        with self._lock:
            norm = self._accounts.validate_new_password_account(email, password)
            user = self._accounts.create(norm, map_source_role("A", "user"), password=password, owns_email=True)
            return user.id

    def bootstrap_admin(self, email, password):
        """Create the first admin. Setup only: refused once any admin exists."""
        with self._lock:
            if self._accounts.has_admin():
                raise AdminExistsError("an admin already exists; ask an admin to change roles")
            norm = self._accounts.validate_new_password_account(email, password)
            user = self._accounts.create(norm, "admin", password=password, owns_email=True)
            return user.id

    # ---- sessions (M02)
    def login_password(self, email, password):
        """Token for the right email and password; AuthError otherwise (same error for every failure)."""
        with self._lock:
            norm = _normalise_email(email)
            user = self._accounts.owner_of(norm)
            stored = user.password_hash if user else None
            pw = password if isinstance(password, str) else ""
            if not self._accounts.hasher.verify(pw, stored) or user is None or pw == "":
                raise AuthError("invalid credentials")
            return self._sessions.issue(user)

    def whoami(self, token):
        """The signed-in user's id, email and current role; AuthError for an invalid session."""
        with self._lock:
            user = self._current_user(token)
            return {"user_id": user.id, "email": user.email, "role": user.role}

    def logout(self, token):
        """Revoke the session. Logging out an unknown or expired token does nothing."""
        with self._lock:
            self._sessions.revoke(token)

    def _current_user(self, token):
        user_id = self._sessions.resolve(token)
        user = self._accounts.get(user_id) if user_id else None
        if user is None:
            raise AuthError("invalid or expired session")
        return user

    # ---- federation (M03, rebuilt from B's behaviour)
    def login_oauth(self, provider, subject, email, email_verified):
        """Sign in with a provider's (already verified) response.

        1. A known (provider, subject) signs in to its linked account.
        2. Else, if the provider says the email is verified, join the account that owns that email.
        3. Else create a separate account (role viewer, B's member). It owns the email only when
           the email is verified and nobody owns it yet, so an unverified email never captures an address.
        """
        if not isinstance(provider, str) or not provider.strip():
            raise AuthError("provider is required")
        if not isinstance(subject, str) or not subject.strip():
            raise AuthError("subject is required")
        key = (provider.strip().lower(), subject.strip())
        norm = _normalise_email(email)
        verified = email_verified is True and norm is not None
        with self._lock:
            link = self._identities.get(key)
            user = self._accounts.get(link["user_id"]) if link else None
            if user is None:
                owner = self._accounts.owner_of(norm) if verified else None
                if owner is not None:
                    user = owner
                else:
                    user = self._accounts.create(norm, map_source_role("B", "member"), owns_email=verified)
                self._identities[key] = {"user_id": user.id, "email_verified": verified}
            return self._sessions.issue(user)

    # ---- access control (M04)
    @staticmethod
    def map_source_role(source_app, role):
        return map_source_role(source_app, role)

    @staticmethod
    def can(role, permission):
        return can(role, permission)

    # ---- role admin (M05, improved from C)
    def set_role(self, token, user_id, role):
        """Change a user's role. Only admins; the role must exist; nobody raises their own role."""
        with self._lock:
            try:
                actor = self._current_user(token)
            except AuthError:
                raise NotAuthenticatedError("a valid admin session is required to change roles") from None
            if not can(actor.role, "manage_roles"):
                raise PermissionError("only admins can change roles")
            _check_role(role)
            target = self._accounts.get(user_id)
            if target is None:
                raise KeyError(user_id)
            if target.id == actor.id and ROLE_RANK[role] > ROLE_RANK[actor.role]:
                raise PermissionError("nobody can raise their own role")
            target.role = role


def create_app(**settings):
    """A new, empty identity system. Optional settings: pbkdf2_iterations, session_ttl_seconds, clock."""
    return IdentityApp(Config(**settings))
