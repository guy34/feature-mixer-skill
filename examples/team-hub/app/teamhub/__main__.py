"""Run Team Hub.

    python3 -m teamhub create-user --email you@example.com --name You --role owner --can-approve
    python3 -m teamhub serve
"""

import argparse
import getpass
import sys

from . import auth, config, db, server
from .errors import AppError


def main(argv=None):
    parser = argparse.ArgumentParser(prog="teamhub")
    parser.add_argument("--db", default=config.DB_PATH)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--host", default=config.HOST)
    s.add_argument("--port", type=int, default=config.PORT)
    u = sub.add_parser("create-user")
    u.add_argument("--email", required=True)
    u.add_argument("--name", required=True)
    u.add_argument("--role", default="member", choices=auth.ROLES)
    u.add_argument("--can-approve", action="store_true")
    args = parser.parse_args(argv)

    conn = db.connect(args.db)
    if args.command == "create-user":
        password = getpass.getpass("Password (8+ characters): ")
        try:
            user = auth.create_user(conn, args.email, args.name, password, args.role, args.can_approve)
        except AppError as e:
            print(f"error: {e.message}")
            return 1
        print(f"created {user['email']} ({user['role']})")
        return 0
    httpd = server.serve(conn, args.host, args.port)
    print(f"Team Hub on http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
