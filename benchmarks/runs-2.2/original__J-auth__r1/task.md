# Scenario J: authentication from three apps

Combine the sign-in of three apps into one identity system:

- **A (Passbook)**, `sources/passbook`: email and password accounts, own code.
- **B (Linkup)**, `sources/linkup`: sign-in with an OAuth provider (Google-style), MIT.
- **C (Roster)**, `sources/roster`: roles and permissions (viewer, editor, admin), own code.

The user's decisions (already given, record them):
- One account per person. A federated sign-in joins an existing account **only** when the provider says the
  email is verified; otherwise it is a separate account.
- Roles: A's `user` becomes `editor`; B's `member` becomes `viewer`; C's roles keep their names.
  Only an admin can change roles. Nobody can raise their own role.

Build the unified module as `unified/identity.py` exposing exactly this interface (the scenario's hidden tests
use it):

```python
app = create_app()
app.register_password(email, password) -> user_id
app.login_password(email, password) -> token            # raises AuthError on failure
app.login_oauth(provider, subject, email, email_verified) -> token
app.whoami(token) -> {"user_id": ..., "email": ..., "role": ...}   # raises AuthError if invalid
app.logout(token)
app.set_role(token, user_id, role)                      # raises PermissionError unless the caller is admin
app.map_source_role(source_app, role) -> unified role   # raises KeyError for an unknown role
app.bootstrap_admin(email, password) -> user_id         # creates the first admin (setup only)
```
`AuthError` must be importable from the module. Standard library only.
