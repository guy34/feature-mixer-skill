# OpenForum API (illustrative). JWT bearer tokens; posts publish immediately; anonymous posting allowed.
import jwt

def login(db, email, password):
    user = db.check(email, password)
    return {"token": jwt.encode({"sub": user["id"], "role": user["role"]}, "secret")}

def get_post(db, post_id):            # GET /api/posts/<int:post_id>  -> {"id": int, "body": str, "author_id": int|None}
    return db.get("posts", post_id)

def create_post(db, body, token=None):  # POST /api/posts  (no token = anonymous post, published at once)
    if len(body) > 10000:
        raise ValueError("too long")
    author = jwt.decode(token, "secret")["sub"] if token else None
    return db.insert("posts", author_id=author, body=body)

ROUTES = {"GET /api/posts/<int:post_id>": get_post, "POST /api/posts": create_post, "POST /api/token": login}
CLIENT_ROUTES = ["/posts", "/login"]
