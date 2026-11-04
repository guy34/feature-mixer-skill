# OpenForum models (illustrative, SQL shown as comments)
# users: id integer primary key, email text, name text, role text ('user' | 'admin')
# posts: id integer primary key, author_id integer null (null = anonymous), body text (max 10000), created_at timestamp
MAX_POST_LENGTH = 10000
ROLES = ("user", "admin")
