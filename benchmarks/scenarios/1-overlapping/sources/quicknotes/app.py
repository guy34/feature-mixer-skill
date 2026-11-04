# QuickNotes HTTP handlers (Flask-style, illustrative)
from markdown import render

def list_notes(db): return db.all("select * from notes order by created_at desc")
def create_note(db, title, body): return db.insert("notes", title=title, body=body)
def update_note(db, note_id, title, body): return db.update("notes", note_id, title=title, body=body)
def delete_note(db, note_id): return db.delete("notes", note_id)

def tag_note(db, note_id, tag_name):
    tag = db.get_or_create("tags", name=tag_name)
    db.insert("note_tags", note_id=note_id, tag_id=tag["id"])

def search(db, text):
    # full-text search over title and body
    return db.all("select * from notes where title like ? or body like ?", (f"%{text}%", f"%{text}%"))

def preview(note):
    # renders the Markdown body to HTML for the preview pane
    return render(note["body"])

ROUTES = {"GET /notes": list_notes, "POST /notes": create_note, "PUT /notes/<id>": update_note,
          "DELETE /notes/<id>": delete_note, "POST /notes/<id>/tags": tag_note, "GET /search": search,
          "GET /notes/<id>/preview": preview}
