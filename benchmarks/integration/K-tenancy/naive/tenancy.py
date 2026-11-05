# Naive: B's single-tenant project code reused as it was; org_id stored but never used to filter.
import itertools


class App:
    def __init__(self):
        self.ids = itertools.count(1)
        self.users, self.projects, self.resources, self.templates = {}, {}, {}, {}

    def create_org(self, name):
        return next(self.ids)

    def add_user(self, org_id, name):
        i = next(self.ids); self.users[i] = {"org_id": org_id}; return i

    def create_project(self, user_id, name):
        i = next(self.ids)
        self.projects[i] = {"id": i, "name": name, "org_id": self.users[user_id]["org_id"]}
        return i

    def list_projects(self, user_id):
        return list(self.projects.values())

    def get_project(self, user_id, project_id):
        return self.projects[project_id]

    def add_resource(self, user_id, project_id, data):
        i = next(self.ids); self.resources[i] = {"id": i, "project_id": project_id, "data": data}; return i

    def list_resources(self, user_id, project_id=None):
        return [r for r in self.resources.values() if project_id is None or r["project_id"] == project_id]

    def search(self, user_id, text):
        return [x for x in list(self.projects.values()) + list(self.resources.values())
                if text in str(x.get("name", x.get("data")))]

    def create_template(self, name):
        i = next(self.ids); self.templates[i] = {"id": i, "name": name}; return i

    def list_templates(self, user_id):
        return list(self.templates.values())

    def update_template(self, user_id, template_id, name):
        self.templates[template_id]["name"] = name


def create_app():
    return App()
