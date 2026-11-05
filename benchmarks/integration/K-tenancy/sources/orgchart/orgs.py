ORGS, MEMBERS = {}, {}   # MEMBERS: user_id -> org_id
def members_of(org_id):
    return [u for u, o in MEMBERS.items() if o == org_id]
