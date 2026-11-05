import json, os, sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

DB = sqlite3.connect(os.environ.get("SHELFIE_DB", "shelfie.db"))
SECRET = os.environ["SHELFIE_SESSION_SECRET"]          # required, not documented anywhere
DB.execute("create table if not exists books (id integer primary key, title text not null, author text)")
DB.execute("create table if not exists ratings (book_id integer references books(id), stars integer "
           "check (stars between 1 and 5))")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/books":
            rows = DB.execute("select id, title, author from books").fetchall()
            self._json([{"id": r[0], "title": r[1], "author": r[2]} for r in rows])
        elif self.path == "/api/books/export":            # JSON, not CSV
            rows = DB.execute("select b.title, r.stars from books b left join ratings r on r.book_id = b.id")
            self._json([{"title": t, "stars": s} for t, s in rows])

    def do_PUT(self):
        if self.path.startswith("/api/books/") and self.path.endswith("/rating"):
            book_id = int(self.path.split("/")[3])
            stars = int(json.loads(self.rfile.read(int(self.headers["Content-Length"])))["stars"])
            if not 1 <= stars <= 5:
                return self._json({"error": "stars must be 1 to 5"}, 400)
            DB.execute("insert into ratings values (?, ?)", (book_id, stars))
            self._json({"ok": True})

    def _json(self, body, status=200):
        self.send_response(status); self.end_headers(); self.wfile.write(json.dumps(body).encode())


if __name__ == "__main__":
    HTTPServer(("", 8080), Handler).serve_forever()
