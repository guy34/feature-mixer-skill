# Single-tenant: one customer per installation, so nothing is filtered.
PROJECTS, RESOURCES = {}, {}
def list_projects():
    return list(PROJECTS.values())
def get_project(pid):
    return PROJECTS[pid]
