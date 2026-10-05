"""Where the backend under test lives, and who the personas are.

Everything here comes from docs/system.md ("Personas", "Clone contract"). The suite never holds a
real HF token: personas are the fake tokens that both the bridge and the clone understand.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_BACKEND_URL = "http://127.0.0.1:8200"
BRIDGE_URL = "http://127.0.0.1:8100"
HF_ORIGIN = "https://huggingface.co"

ROOT = Path(__file__).resolve().parents[3]  # repo root (conformance/src/conformance/config.py)
OBSERVATIONS = ROOT / "docs" / "hf-gated" / "observations"
CONFORMANCE = ROOT / "conformance"
REPORTS = CONFORMANCE / "reports"
DIVERGENCES_FILE = CONFORMANCE / "divergences.yaml"
SCENARIOS_FILE = CONFORMANCE / "scenarios.yaml"


def backend_url() -> str:
    return os.environ.get("BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


# Persona -> bearer token sent to the backend (None = no Authorization header).
# docs/system.md "Personas"; persona-carol is the clone-only third user ("Built-in seeds").
TOKENS: dict[str, str | None] = {
    "anonymous": None,
    "owner": "persona-owner",
    "requester": "persona-requester",
    "carol": "persona-carol",
    # Any other bearer value must be refused like HF refuses an invalid token (system.md).
    "bad": "conformance-invalid-token",
}

# Identity names found in the recordings -> persona.
# probe.py records the env-var name of the token (`as`), the bridge log records the persona.
IDENTITY_ALIASES = {
    "anonymous": "anonymous",
    "OWNER": "owner",
    "HF_OWNER_ACCESS_TOKEN": "owner",
    "owner": "owner",
    "REQUESTER": "requester",
    "HF_REQUESTER_ACCESS_TOKEN": "requester",
    "requester": "requester",
    "BAD_TOKEN": "bad",
}

# Origins a recording may carry in absolute URLs (Location, Link, request URLs).
RECORDED_ORIGINS = (HF_ORIGIN, BRIDGE_URL)


def auth_headers(persona: str) -> dict[str, str]:
    token = TOKENS[persona]
    return {} if token is None else {"Authorization": f"Bearer {token}"}
