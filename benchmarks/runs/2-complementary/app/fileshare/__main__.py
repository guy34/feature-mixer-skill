"""Run locally: python3 -m fileshare (settings from FILESHARE_* environment variables)."""

import logging
from wsgiref.simple_server import make_server

from .config import Config
from .web import App


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = Config.from_env()
    app = App(config)
    with make_server(config.host, config.port, app) as server:
        print(f"FileShare on http://{config.host}:{config.port}/")
        server.serve_forever()


if __name__ == "__main__":
    main()
