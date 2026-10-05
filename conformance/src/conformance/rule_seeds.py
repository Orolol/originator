"""Seeds for the rule tests: our own demo repos and users, in the documented seed format.

These repos do not exist on huggingface.co (like the clone's built-in demos); their names and gate
forms are ours, so the tests know every label and file without reading the clone's fixtures.
"""

from __future__ import annotations

import copy
import hashlib

from .seeds import CAROL, base_users, request, sandbox_repo, seed

OWNER = "Orosius"
REQUESTER = "TestingBOrig"
MANUAL = "Orosius/conf-manual"
AUTO = "Orosius/conf-auto"
FORM = "Orosius/conf-form"
PUBLIC = "Orosius/conf-public"
NOW = "2026-10-05T15:00:00.000Z"

ALLOWLISTED = ("README.md", "LICENSE", "LICENSE.md", "LICENSE.txt")
NOT_ALLOWLISTED = (
    ".gitattributes", "config.json", "readme.md", "README.MD", "README.txt", "README", "LICENSE.rst",
    "license.txt", "LICENCE", "COPYING", "sub/README.md", "sub/LICENSE.txt",
)
FORM_FIELDS = {
    "Company": "text",
    "Country": "country",
    "Date of birth": "date_picker",
    "Job title": {"type": "select", "options": ["Student", "Researcher", "Other"]},
    "I agree to share my contact information": "checkbox",
}
FORM_ANSWERS = {
    "Company": "Acme Research",
    "Country": "FR",
    "Date of birth": "1990-01-31",
    "Job title": "Researcher",
    "I agree to share my contact information": "on",
}
AUTO_FIELDS = {"I accept the license": "checkbox"}


def text_file(path: str, text: str | None = None) -> dict:
    text = text if text is not None else f"content of {path}\n"
    data = text.encode()
    return {"text": text, "oid": hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(), "size": len(data)}


def demo_repo(repo_id: str, gated, files: tuple[str, ...], card: dict | None = None, _id: str = "") -> dict:
    return {
        "id": repo_id, "_id": _id, "author": repo_id.split("/")[0], "private": False, "gated": gated,
        "orgMembersGated": False, "gatedNotificationsMode": "bulk", "gatedNotificationsEmail": None,
        "sha": hashlib.sha1(f"conformance-demo:{repo_id}".encode()).hexdigest(),
        "createdAt": "2026-01-01T00:00:00.000Z", "lastModified": "2026-01-02T00:00:00.000Z",
        "cardData": card or {"license": "mit"}, "info": {},
        "files": {path: text_file(path) for path in files},
    }


def extra_users(count: int) -> list[dict]:
    return [
        {"user": f"conf-user-{i:02d}", "_id": f"64b0c0ffee000000000a{i:04x}", "fullname": f"Conformance User {i:02d}",
         "email": f"user{i:02d}@conformance.test", "avatarUrl": f"/avatars/conf-user-{i:02d}.svg", "isPro": False,
         "token": f"conformance-token-{i:02d}", "orgs": []}
        for i in range(1, count + 1)
    ]


def rules_seed(requests: list[dict] | None = None, users: int = 0, now: str = NOW, tick_ms: int = 1000) -> dict:
    files = (*ALLOWLISTED, *NOT_ALLOWLISTED)
    repos = [
        copy.deepcopy(sandbox_repo()),
        demo_repo(MANUAL, "manual", files, _id="64b0c0ffee0000000000d001"),
        demo_repo(AUTO, "auto", ("README.md", "config.json"),
                  {"license": "mit", "extra_gated_fields": AUTO_FIELDS}, _id="64b0c0ffee0000000000d002"),
        demo_repo(FORM, "manual", ("README.md", "config.json"),
                  {"license": "mit", "extra_gated_fields": FORM_FIELDS,
                   "extra_gated_heading": "Conformance form", "extra_gated_button_content": "Send"},
                  _id="64b0c0ffee0000000000d003"),
        demo_repo(PUBLIC, False, ("README.md", "config.json"),
                  {"license": "mit", "extra_gated_description": "stale description (CFG-5)"},
                  _id="64b0c0ffee0000000000d004"),
    ]
    document = seed("conformance:rules", now, list(requests or []), repos, tick_ms=tick_ms)
    document["users"] = base_users() + extra_users(users)
    return document


def pending(user: str, timestamp: str, repo: str = MANUAL, **kwargs) -> dict:
    return request(user, "pending", timestamp, repo=repo, **kwargs)


__all__ = [
    "ALLOWLISTED", "AUTO", "AUTO_FIELDS", "CAROL", "FORM", "FORM_ANSWERS", "FORM_FIELDS", "MANUAL", "NOT_ALLOWLISTED",
    "NOW", "OWNER", "PUBLIC", "REQUESTER", "demo_repo", "extra_users", "pending", "request", "rules_seed", "text_file",
]
