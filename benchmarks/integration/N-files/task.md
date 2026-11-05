# Scenario N: upload, preview, share and delete

- **A (Dropzone)**, `sources/dropzone`: uploads to object storage, numeric file ids.
- **B (Peek)**, `sources/peek`: previews files from a local disk store, path-based ids.
- **C (Passlink)**, `sources/passlink`: share links; **links never expire** in C.
- Deletion lives in A and does not know about C's links.

User's decisions: one store; opaque ids; files are private to their owner by default; share links expire
(the owner chooses the lifetime); deleting a file revokes its links and leaves no broken previews.

Build `unified/files.py`:

```python
app = create_app(clock)                    # clock(): current time in seconds (tests move it)
fid = app.upload(user, name, data_bytes)
app.preview(user, fid) -> bytes            # first 64 bytes; PermissionError for non-owners, KeyError once deleted
token = app.share(user, fid, seconds)      # PermissionError unless owner
app.open_link(token) -> bytes              # PermissionError when expired, revoked or unknown
app.delete(user, fid)                      # PermissionError unless owner
app.attach(user, note, fid); app.attachments(user, note) -> [{"file": fid, "status": "ok" | "deleted"}]
```
