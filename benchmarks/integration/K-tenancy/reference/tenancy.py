import itertools


class App:
    def __init__(self):
        self.ids = itertools.count(1)
        self.orgs, self.users, self.projects, self.resources, self.templates = {}, {}, {}, {}, {}

    def create_org(self, name):
        i = next(self.ids); self.orgs[i] = {"id": i, "name": name}; return i

    def add_user(self, org_id, name):
        i = next(self.ids); self.users[i] = {"id": i, "org_id": org_id, "name": name}; return i

    def _org(self, user_id):
        return self.users[user_id]["org_id"]

    def _own_project(self, user_id, project_id):
        p = self.projects.get(project_id)
        if p is None or p["org_id"] != self._org(user_id):
            raise PermissionError("not your organisation's project")
        return p

    def create_project(self, user_id, name):
        i = next(self.ids); self.projects[i] = {"id": i, "name": name, "org_id": self._org(user_id)}; return i

    def list_projects(self, user_id):
        return [dict(p) for p in self.projects.values() if p["org_id"] == self._org(user_id)]

    def get_project(self, user_id, project_id):
        return dict(self._own_project(user_id, project_id))

    def add_resource(self, user_id, project_id, data):
        p = self._own_project(user_id, project_id)
        i = next(self.ids)
        self.resources[i] = {"id": i, "project_id": project_id, "org_id": p["org_id"], "data": data}
        return i

    def list_resources(self, user_id, project_id=None):
        if project_id is not None:
            self._own_project(user_id, project_id)
        org = self._org(user_id)
        return [dict(r) for r in self.resources.values() if r["org_id"] == org and
                (project_id is None or r["project_id"] == project_id)]

    def search(self, user_id, text):
        t = text.lower()
        return [p for p in self.list_projects(user_id) if t in p["name"].lower()] + \
               [r for r in self.list_resources(user_id) if t in r["data"].lower()]

    def create_template(self, name):
        i = next(self.ids); self.templates[i] = {"id": i, "name": name}; return i

    def list_templates(self, user_id):
        return [dict(t) for t in self.templates.values()]

    def update_template(self, user_id, template_id, name):
        raise PermissionError("shared templates are read-only")


def create_app():
    return App()
