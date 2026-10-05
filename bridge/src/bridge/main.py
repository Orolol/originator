"""Entry point: `uv run --project bridge bridge`."""

import uvicorn

from .app import create_app
from .config import Settings


def run() -> None:
    settings = Settings.from_env()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
