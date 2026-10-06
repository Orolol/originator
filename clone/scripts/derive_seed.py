"""Derive the built-in `sandbox` seed from the recorded fixtures. Run from the repo root:

    uv run --project clone python clone/scripts/derive_seed.py

Writes `clone/src/clone/seeds/sandbox.json` and `clean.json` (committed; the clone only reads them).

Sources (ground truth, `docs/hf-gated/observations/`):
- `2026-10-06-clone-seed-reads.json`: model info (incl. the siblings), top-level and one
  sub-folder tree, whoami of both personas, the contents of three small files, the HEAD of one
  LFS file (`X-Linked-Etag` / `X-Linked-Size`, xet hash in the redirect path).
- `2026-10-06-ui-walkthrough.json`: the requester's request at the end of the scripted UI
  walkthrough (back to `pending`, AGENTS.md "Live sandbox").

What the fixtures do not give is left out of the seed (no fabricated oids or sizes): the clone
synthesises deterministic stub metadata for those files at load time (`src/clone/files.py`).
E-mails are redacted in the recordings, so the users get the placeholder addresses of
docs/system.md. The demo repos and `DemoCarol` are clone-only (docs/system.md "Built-in seeds");
they do not exist on huggingface.co.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
OBS = ROOT / "docs" / "hf-gated" / "observations"
SEEDS = ROOT / "clone" / "src" / "clone" / "seeds"
OUT = SEEDS / "sandbox.json"
OUT_CLEAN = SEEDS / "clean.json"

OWNER = "OwnerOfTheGatedModel"
REPO = f"{OWNER}/tiny-gated-model"
# Keys of the model-info body that the seed format keeps at repo level (docs/system.md seed format).
REPO_LEVEL = ("_id", "id", "author", "private", "gated", "sha", "createdAt", "lastModified", "cardData")


def records(name: str) -> dict[str, dict]:
    data = json.loads((OBS / name).read_text())
    return {r["id"]: r for r in data["records"]}


def lfs_patterns(gitattributes: str) -> list[str]:
    return [line.split()[0] for line in gitattributes.splitlines() if "filter=lfs" in line]


def is_lfs(path: str, patterns: list[str]) -> bool:
    name = path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatchcase(name, p) or fnmatch.fnmatchcase(path, p) for p in patterns)


def sandbox_repo(reads: dict[str, dict]) -> dict:
    info = reads["model-info-anon"]["body_json"]
    assert info == reads["model-info-owner"]["body_json"], "model info differs between personas"
    repo = {k: info[k] for k in REPO_LEVEL}
    repo |= {
        "orgMembersGated": False,
        # The last notification PUT of the UI walkthrough was `bulk`; no email was ever set.
        "gatedNotificationsMode": "bulk",
        "gatedNotificationsEmail": None,
    }
    repo["info"] = {k: v for k, v in info.items() if k not in REPO_LEVEL and k != "siblings"}

    tree_main = reads["tree-main"]["body_json"]
    repo["dirs"] = {e["path"]: {"oid": e["oid"]} for e in tree_main if e["type"] == "directory"}

    texts = {
        urlsplit(reads[rid]["url"]).path.split("/resolve/main/", 1)[1]: reads[rid]["body_text"]
        for rid in ("owner-readme", "owner-gitattributes", "owner-config")
    }
    patterns = lfs_patterns(texts[".gitattributes"])

    known: dict[str, dict] = {}
    for entry in tree_main + reads["tree-subdir"]["body_json"]:
        if entry["type"] == "file":
            known[entry["path"]] = {"oid": entry["oid"], "size": entry["size"]}
            if "lfs" in entry:
                known[entry["path"]]["lfs"] = {"size": entry["lfs"]["size"], "pointerSize": entry["lfs"]["pointerSize"]}

    # The tree masks the LFS sha256 and xet hash (64 '*'); the HEAD of the same file shows them.
    head = reads["owner-head-lfs"]
    lfs_path = urlsplit(head["url"]).path.split("/resolve/main/", 1)[1]
    assert int(head["headers"]["x-linked-size"]) == known[lfs_path]["size"]
    known[lfs_path]["lfs"]["oid"] = head["headers"]["x-linked-etag"].strip('"')
    known[lfs_path]["xetHash"] = urlsplit(head["headers"]["location"]).path.rsplit("/", 1)[1]

    files: dict[str, dict] = {}
    for sibling in info["siblings"]:
        path = sibling["rfilename"]
        entry = dict(known.get(path, {}))
        if path in texts:
            entry["text"] = texts[path]
        if "lfs" not in entry and path not in known and is_lfs(path, patterns):
            entry["lfs"] = True  # LFS per the recorded .gitattributes; metadata synthesised
        files[path] = entry
    repo["files"] = files
    return repo


def user(whoami: dict, token: str, email: str) -> dict:
    return {
        "user": whoami["name"],
        "_id": whoami["id"],
        "fullname": whoami["fullname"],
        "email": email,
        "avatarUrl": whoami["avatarUrl"],
        "isPro": whoami["isPro"],
        "token": token,
        "orgs": whoami["orgs"],
        # Other whoami-v2 fields, served verbatim.
        "whoami": {k: v for k, v in whoami.items()
                   if k not in ("type", "id", "name", "fullname", "email", "avatarUrl", "isPro", "orgs")},
    }


def last_pending_request() -> dict:
    log = json.loads((OBS / "2026-10-06-ui-walkthrough.json").read_text())
    lists = [e for e in log if e["path"].endswith("/user-access-request/pending") and e["status"] == 200]
    (item,) = lists[-1]["response_body"]
    assert item["user"]["user"] == "TestingBOrig" and item["status"] == "pending"
    return {"repo": REPO, "user": "TestingBOrig", "status": "pending", "timestamp": item["timestamp"],
            "reviewedAt": None, "grantedBy": None, "fields": None, "emailShared": True}


def demo_hex(name: str, length: int) -> str:
    return hashlib.sha1(f"clone-demo:{name}".encode()).hexdigest()[:length]


def readme(card: dict) -> str:
    """README.md whose YAML front matter is the card metadata (gate-form.md: the gate form is
    configured in the README YAML). JSON is valid YAML, so values are emitted as JSON."""
    lines = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in card.items()] + ["---", ""]
    return "\n".join(lines)


def demo_repo(name: str, gated, card: dict) -> dict:
    repo_id = f"{OWNER}/{name}"
    return {
        "id": repo_id, "_id": demo_hex(repo_id, 24), "author": OWNER, "private": False, "gated": gated,
        "orgMembersGated": False, "gatedNotificationsMode": "bulk", "gatedNotificationsEmail": None,
        "sha": demo_hex(repo_id + "@sha", 40),
        "createdAt": "2026-10-05T12:00:00.000Z", "lastModified": "2026-10-05T12:00:00.000Z",
        "cardData": card,
        "info": {"tags": [f"license:{card['license']}", "region:us"], "downloads": 0, "likes": 0,
                 "modelId": repo_id, "disabled": False, "model-index": None, "config": {}, "spaces": []},
        "files": {
            "README.md": {"text": readme(card)},
            "config.json": {"text": '{\n  "model_type": "demo"\n}\n'},
            "model.safetensors": {"lfs": True},
        },
    }


# Shaped after the live examples of gate-form.md §4 (starcoder: auto + one checkbox; Llama-3.2-1B:
# every field type; gemma: custom heading and button; Mistral: stale metadata on a non-gated repo).
DEMOS = [
    demo_repo("gated-auto-demo", "auto", {
        "license": "mit",
        "extra_gated_prompt": "## Demo license agreement\nPlease read the demo license before accepting it.",
        "extra_gated_fields": {"I accept the above license agreement": "checkbox"},
    }),
    demo_repo("gated-form-demo", "manual", {
        "license": "other",
        "extra_gated_heading": "Request access to the form demo",
        "extra_gated_description": "The information you provide is only used to review your request.",
        "extra_gated_button_content": "Send request",
        "extra_gated_prompt": "### Demo community license\n\nYou may use this model for evaluation only.",
        "extra_gated_fields": {
            "First Name": "text",
            "Last Name": "text",
            "Date of birth": "date_picker",
            "Country": "country",
            "Affiliation": "text",
            "Job title": {"type": "select", "options": [
                "Student", "Researcher", {"label": "Engineer", "value": "engineer"}, "Other"]},
            "geo": "ip_location",
            "I accept the terms of the license": "checkbox",
        },
    }),
    demo_repo("not-gated-demo", False, {
        "license": "apache-2.0",
        "extra_gated_description": "Stale description left from when this repo was gated (CFG-5: ignored).",
    }),
]

CAROL = {
    "user": "DemoCarol", "_id": demo_hex("DemoCarol", 24), "fullname": "Carol Demo",
    "email": "carol@example.com", "avatarUrl": f"/avatars/{demo_hex('DemoCarol-avatar', 32)}.svg",
    "isPro": False, "token": "persona-carol", "orgs": [],
    "whoami": {"emailVerified": True, "canPay": False, "billingMode": "prepaid",
               "auth": {"type": "access_token", "accessToken": {
                   "displayName": "clone", "role": "write", "createdAt": "2026-10-05T12:00:00.000Z"}}},
}


def build_seed() -> dict:
    reads = records("2026-10-06-clone-seed-reads.json")
    return {
        "seed": "sandbox",
        "now": "2026-10-06T16:00:00.000Z",
        "tick_ms": 1000,
        "users": [
            user(reads["whoami-owner"]["body_json"], "persona-owner", "ownerofthegatedmodel@example.com"),
            user(reads["whoami-requester"]["body_json"], "persona-requester", "testingborig@example.com"),
            CAROL,
        ],
        "repos": [sandbox_repo(reads), *DEMOS],
        "requests": [last_pending_request()],
    }


def build_clean_seed() -> dict:
    """The default seed: the same repos and users as `sandbox`, and no access request at all, so a
    reset (or a restart) gives a clean state where nobody has asked for access yet."""
    return {**build_seed(), "seed": "clean", "requests": []}


def main() -> None:
    seed = build_seed()
    OUT.write_text(json.dumps(seed, indent=1, ensure_ascii=False) + "\n")
    OUT_CLEAN.write_text(json.dumps(build_clean_seed(), indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(seed['repos'][0]['files'])} files in {REPO}) and {OUT_CLEAN.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
