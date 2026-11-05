# Scenario L: editing submitted documents

- **A (Drafty)**, `sources/drafty`: authors may edit a document after submitting it.
- **B (Lockbox)**, `sources/lockbox`: a submitted document is locked.
- **C (Override)**, `sources/override`: administrators may override locks.

These rules contradict each other. The user's decision: **submitted documents are locked for their authors;
an administrator may edit a submitted document only with a written reason, and every override is recorded.**
Drafts stay editable by their author. Nobody else edits a draft.

Build `unified/documents.py`:

```python
app = create_app()
app.add_user(user_id, role)                 # role: "author" or "admin"
doc_id = app.create(user_id, text)          # a draft owned by user_id
app.edit(user_id, doc_id, text, reason=None)
app.submit(user_id, doc_id)
app.get(doc_id) -> {"text", "status": "draft" | "submitted", "owner"}
app.audit(doc_id) -> [{"user", "action", "reason"}...]
```
`edit` raises `Locked` (importable from the module) when the rules forbid the edit, and `PermissionError` when
the user may never edit that document.
