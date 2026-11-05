"""Roles module (menu M04): the unified role set, the one permission check, and the source-role mapping.

Adapted from Roster (C, the user's own code): roles as permission sets and a deny-by-default check.
Added: role ranks (to stop anyone raising their own role) and the mapping from every source app's roles,
as the user decided: Passbook (A) user -> editor, Linkup (B) member -> viewer, Roster (C) roles unchanged.
"""

ROLES = {
    "viewer": frozenset({"read"}),
    "editor": frozenset({"read", "write"}),
    "admin": frozenset({"read", "write", "manage_roles"}),
}

# Higher number = more powerful. Used to refuse raising one's own role.
RANK = {"viewer": 0, "editor": 1, "admin": 2}

# Every source role, by source app, mapped to a unified role (architecture.json auth.role_mapping).
ROLE_MAPPING = {
    "A": {"user": "editor"},
    "B": {"member": "viewer"},
    "C": {"viewer": "viewer", "editor": "editor", "admin": "admin"},
}

# Names a caller may use for a source app.
SOURCE_APP_NAMES = {
    "a": "A", "passbook": "A",
    "b": "B", "linkup": "B",
    "c": "C", "roster": "C",
}


def is_role(role):
    return isinstance(role, str) and role in ROLES


def can(role, permission):
    """True when the unified role holds the permission. Unknown roles hold nothing (deny by default)."""
    if not isinstance(role, str):
        return False
    return permission in ROLES.get(role, frozenset())


def rank(role):
    return RANK[role]


def map_source_role(source_app, role):
    """Map a source app's role to the unified role. Raises KeyError for an unknown app or role."""
    if not isinstance(source_app, str) or not isinstance(role, str):
        raise KeyError((source_app, role))
    app_id = SOURCE_APP_NAMES.get(source_app.strip().lower())
    if app_id is None:
        raise KeyError(source_app)
    mapping = ROLE_MAPPING[app_id]
    key = role.strip().lower()
    if key not in mapping:
        raise KeyError(role)
    return mapping[key]
