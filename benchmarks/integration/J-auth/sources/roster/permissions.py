ROLES = {"viewer": {"read"}, "editor": {"read", "write"}, "admin": {"read", "write", "manage_roles"}}
def can(role, permission):
    return permission in ROLES.get(role, set())
def set_role(actor_role, target, role):
    if not can(actor_role, "manage_roles"):
        raise PermissionError("only admins manage roles")
    target["role"] = role
