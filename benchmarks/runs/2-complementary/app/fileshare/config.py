"""Configuration: every setting is an environment variable read here (names in .env.example)."""

import os
from dataclasses import dataclass

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # from Uploader (A): uploads over 10 MB are rejected
DEFAULT_LINK_HOURS = 24  # from ShareLink (C)


@dataclass
class Config:
    db_path: str = "fileshare.sqlite3"
    host: str = "127.0.0.1"
    port: int = 8000
    secure_cookie: bool = False
    session_hours: int = 24 * 7
    pbkdf2_iterations: int = 200_000

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        return cls(
            db_path=env.get("FILESHARE_DB", cls.db_path),
            host=env.get("FILESHARE_HOST", cls.host),
            port=int(env.get("FILESHARE_PORT", cls.port)),
            secure_cookie=env.get("FILESHARE_SECURE_COOKIE", "0") == "1",
        )
