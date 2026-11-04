"""All settings, read once from the environment (decision D07)."""

import os

DB_PATH = os.environ.get("TEAMHUB_DB", "teamhub.db")
SESSION_IDLE_MINUTES = int(os.environ.get("TEAMHUB_SESSION_IDLE_MINUTES", "30"))
PASSWORD_ITERATIONS = int(os.environ.get("TEAMHUB_PASSWORD_ITERATIONS", "200000"))
HOST = os.environ.get("TEAMHUB_HOST", "127.0.0.1")
PORT = int(os.environ.get("TEAMHUB_PORT", "8000"))
