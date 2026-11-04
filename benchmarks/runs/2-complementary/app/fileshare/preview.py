"""Preview: text, image or none, by extension.

Adapted from Previewer (B, user's own code). Change: B returned /thumbs/<id>.png, which nothing
generated or served; the image URL now points at a route that serves the original image.
"""

from .accounts import current_user
from .core.http import json_response
from .files import get_owned_file, read_content

TEXT_TYPES = (".txt", ".md", ".csv")
IMAGE_TYPES = (".png", ".jpg", ".gif")
MAX_LINES = 20


def build_preview(name, data, image_url):
    lower = name.lower()
    if lower.endswith(TEXT_TYPES):
        return {"kind": "text", "first_lines": data.decode("utf-8", "replace").splitlines()[:MAX_LINES]}
    if lower.endswith(IMAGE_TYPES):
        return {"kind": "image", "url": image_url}
    return {"kind": "none", "reason": "no preview for this type"}


def preview_row(ctx, row, image_url):
    lower = row["name"].lower()
    data = read_content(ctx, row["id"]) if lower.endswith(TEXT_TYPES) else b""
    return build_preview(row["name"], data, image_url)


def owner_preview(ctx, req, file_id):
    user = current_user(ctx, req)
    row = get_owned_file(ctx, user, file_id)
    return json_response(200, preview_row(ctx, row, f"/api/files/{file_id}/content"))
