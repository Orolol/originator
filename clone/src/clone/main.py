"""Entry point: `uv run --project clone clone` (CLONE_HOST, CLONE_PORT, CLONE_PUBLIC_URL)."""

import os

import uvicorn

from .app import create_app


def run() -> None:
    host = os.environ.get("CLONE_HOST", "127.0.0.1")
    port = int(os.environ.get("CLONE_PORT", "8200"))
    # Absolute URLs (ask-access Location, list Link, LFS redirect) use this origin.
    public_url = os.environ.get("CLONE_PUBLIC_URL") or f"http://{host}:{port}"
    uvicorn.run(create_app(public_url=public_url), host=host, port=port, server_header=False, date_header=False)
