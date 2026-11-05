# Unified Identity

One identity system built by Feature Mixer from Passbook (password accounts), Linkup (OAuth sign-in) and Roster
(roles). Python 3.8+, standard library only. The module is `unified/identity.py`:

```python
from unified.identity import create_app, AuthError
app = create_app()
```

Interface: `register_password`, `login_password`, `login_oauth`, `whoami`, `logout`, `set_role`, `map_source_role`,
`bootstrap_admin`. See `../mixer/design/architecture.md`.

## Settings

Copy `.env.example`; every value is optional. `create_app(session_ttl=..., pbkdf2_iterations=...)` overrides them.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

`login_oauth` trusts its arguments: the caller must have verified the provider's ID token (signature, audience,
expiry) first. That provider side is not part of this module and was not tested against a real provider.
