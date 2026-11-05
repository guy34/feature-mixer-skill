# Unified Identity

One identity system combining Passbook (email and password), Linkup (OAuth
sign-in) and Roster (viewer / editor / admin roles). Python 3.8+, standard
library only, in-memory state per app instance.

```python
from unified.identity import create_app, AuthError
app = create_app()
admin_id = app.bootstrap_admin("admin@example.com", "pw")      # setup only
uid = app.register_password("ana@example.com", "pw")           # role editor
token = app.login_password("ana@example.com", "pw")
app.whoami(token)        # {"user_id": uid, "email": "ana@example.com", "role": "editor"}
t2 = app.login_oauth("google", "sub-1", "ana@example.com", True)  # joins ana (verified email)
app.logout(token)
```

Rules: a federated sign-in joins an existing account only when the provider
says the email is verified, otherwise it is a separate viewer account.
Roles: Passbook `user` -> editor, Linkup `member` -> viewer, Roster roles
unchanged. Only an admin can change roles; nobody can raise their own role.

`login_oauth` expects a provider response the caller has already verified
(OAuth redirect, code exchange and ID-token checks are out of scope).

Settings (environment or `create_app(...)`): `IDENTITY_PBKDF2_ITERATIONS`
(default 310000), `IDENTITY_SESSION_TTL_SECONDS` (default 43200).

Tests: `python3 -m unittest discover -s tests -t .` from this folder.
