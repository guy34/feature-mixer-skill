# Scenario K: organisations, projects and shared resources

- **A (Orgchart)**, `sources/orgchart`: organisations and their members (multi-tenant by `org_id`).
- **B (Projector)**, `sources/projector`: projects and their resources (single-tenant: everything is global).
- **C (Commons)**, `sources/commons`: shared templates every customer can use.

User's decisions: every project and resource belongs to exactly one organisation; templates are shared and
read-only for everyone. Nobody may see or change another organisation's data.

Build `unified/tenancy.py` with:

```python
app = create_app()
org_id = app.create_org(name)
user_id = app.add_user(org_id, name)
project_id = app.create_project(user_id, name)
app.list_projects(user_id) -> [project dicts with "id", "name", "org_id"]
app.get_project(user_id, project_id) -> dict          # raises PermissionError for another org's project
app.add_resource(user_id, project_id, data) -> resource_id   # PermissionError across orgs
app.list_resources(user_id, project_id=None) -> [dicts]
app.search(user_id, text) -> [dicts of projects and resources whose name/data contains text]
app.create_template(name) -> template_id                # setup only; shared
app.list_templates(user_id) -> [dicts]
app.update_template(user_id, template_id, name)         # raises PermissionError: shared templates are read-only
```
