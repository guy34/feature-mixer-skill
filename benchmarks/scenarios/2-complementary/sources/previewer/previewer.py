"""Previewer: make a preview for a stored file (illustrative)."""
TEXT_TYPES = (".txt", ".md", ".csv")
IMAGE_TYPES = (".png", ".jpg", ".gif")

def preview(file):
    name = file["name"].lower()
    if name.endswith(TEXT_TYPES):
        return {"kind": "text", "first_lines": file["data"].decode("utf-8", "replace").splitlines()[:20]}
    if name.endswith(IMAGE_TYPES):
        return {"kind": "image", "thumbnail": f"/thumbs/{file['id']}.png"}
    return {"kind": "none", "reason": "no preview for this type"}
