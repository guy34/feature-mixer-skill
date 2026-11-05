# Sign in with a provider. Accounts are keyed by (provider, subject). The provider sends email and email_verified.
ACCOUNTS = {}  # (provider, subject) -> {"id", "email", "role": "member"}
def callback(provider, subject, email, email_verified):
    key = (provider, subject)
    if key not in ACCOUNTS:
        ACCOUNTS[key] = {"id": f"lu-{len(ACCOUNTS) + 1}", "email": email, "role": "member"}
    return ACCOUNTS[key]
