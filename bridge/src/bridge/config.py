"""Bridge configuration: environment variables plus the repo-root `.env` file.

Precedence: process environment > `.env` file > defaults. Token values only ever live in
`Settings.tokens` (never in `repr`, health output or logs).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import httpx

# bridge/src/bridge/config.py -> repo root is three levels above the package directory.
REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_UPSTREAM = "https://huggingface.co"
DEFAULT_PUBLIC_URL = "http://127.0.0.1:8100"
DEFAULT_REPOS = "Orosius/deltanet-mla-latent"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8100
DEFAULT_LOG_FILE = REPO_ROOT / "harness" / "recordings" / "raw" / "bridge.jsonl"

# Persona name -> env var holding the real token (docs/system.md "Personas").
PERSONA_TOKEN_VARS = {
    "owner": "HF_OWNER_ACCESS_TOKEN",
    "requester": "HF_REQUESTER_ACCESS_TOKEN",
}


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines. Comments, blank lines and surrounding quotes are handled."""
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def normalize_origin(url: str, name: str) -> str:
    """Return `scheme://host[:port]` without a trailing slash; reject anything with a path."""
    parsed = httpx.URL(url)
    if parsed.scheme not in ("http", "https") or not parsed.host:
        raise ValueError(f"{name} must be an http(s) URL, got {url!r}")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError(f"{name} must be an origin without path or query, got {url!r}")
    return url.rstrip("/")


@dataclass(frozen=True)
class Settings:
    upstream: str = DEFAULT_UPSTREAM
    public_url: str = DEFAULT_PUBLIC_URL
    repos: tuple[str, ...] = (DEFAULT_REPOS,)
    # persona name -> real HF token. Absent persona = not configured.
    tokens: Mapping[str, str] = field(default_factory=dict, repr=False)
    log_file: Path | None = DEFAULT_LOG_FILE
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        environ = os.environ if environ is None else environ
        explicit_env_file = environ.get("BRIDGE_ENV_FILE")
        env_file = Path(explicit_env_file) if explicit_env_file else REPO_ROOT / ".env"
        if env_file.is_file():
            values = {**parse_env_file(env_file), **environ}
        elif explicit_env_file:
            raise FileNotFoundError(f"BRIDGE_ENV_FILE does not exist: {env_file}")
        else:
            values = dict(environ)

        repos = tuple(r.strip() for r in values.get("BRIDGE_REPOS", DEFAULT_REPOS).split(",") if r.strip())
        if not repos:
            raise ValueError("BRIDGE_REPOS is empty: the bridge would refuse every repo-scoped call")

        log_file = values.get("BRIDGE_LOG_FILE")
        return cls(
            upstream=normalize_origin(values.get("BRIDGE_UPSTREAM") or DEFAULT_UPSTREAM, "BRIDGE_UPSTREAM"),
            public_url=normalize_origin(values.get("BRIDGE_PUBLIC_URL") or DEFAULT_PUBLIC_URL, "BRIDGE_PUBLIC_URL"),
            repos=repos,
            tokens={p: values[var] for p, var in PERSONA_TOKEN_VARS.items() if values.get(var)},
            log_file=DEFAULT_LOG_FILE if log_file is None else (Path(log_file) if log_file else None),
            host=values.get("BRIDGE_HOST") or DEFAULT_HOST,
            port=int(values.get("BRIDGE_PORT") or DEFAULT_PORT),
        )
