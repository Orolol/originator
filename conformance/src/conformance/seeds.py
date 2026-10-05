"""Initial states (clone seed documents) written from the recordings, never from the clone.

Seed format: docs/system.md "Seed format". Everything static (users, the sandbox repo, its files) is
derived programmatically from the recordings, so a typo cannot creep in:

- users: `whoami-*` and list items in `2026-10-05-clone-seed-reads.json` / the walkthroughs;
- sandbox repo: `model-info-anon`, `tree-main`, `tree-subdir`, and the `body_text` of small files
  in `2026-10-05-clone-seed-reads.json`;
- stand-in repos (other real repos probed anonymously): ids, `_id` and `gated` from
  `2026-10-05-anonymous-probes.json`; file *contents* are stubs (the recorded 160-character excerpt),
  so only status, error headers and allowlist decisions are meaningful for them.

The request state at the start of each recording is written per scenario (see SCENARIO_STATES)
from what the recording's first steps show.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from functools import cache
from typing import Any

from .config import OBSERVATIONS

SANDBOX = "Orosius/deltanet-mla-latent"
OWNER_EMAIL = "orosius@example.com"
REQUESTER_EMAIL = "testingborig@example.com"
CAROL = "DemoCarol"
CAROL_EMAIL = "carol@example.org"

# Top-level repo keys of the seed format; every other model-info field goes to `info`, verbatim.
REPO_KEYS = ("_id", "id", "author", "private", "gated", "sha", "createdAt", "lastModified", "cardData")


@cache
def _records(file_name: str) -> dict[str, dict]:
    data = json.loads((OBSERVATIONS / file_name).read_text())
    return {r["id"]: r for r in data["records"]}


def _seed_reads() -> dict[str, dict]:
    return _records("2026-10-05-clone-seed-reads.json")


# whoami-v2 fields that are not part of the documented user record. The clone's seed format carries
# them under `whoami` (seen through GET /__clone__/state: key names only; the values are the recording's).
WHOAMI_IDENTITY = ("type", "id", "name", "fullname", "email", "isPro", "avatarUrl", "orgs")


def _user_from_whoami(whoami: dict, email: str, token: str) -> dict:
    return {
        "user": whoami["name"],
        "_id": whoami["id"],
        "fullname": whoami["fullname"],
        "email": email,
        "avatarUrl": whoami["avatarUrl"],
        "isPro": whoami["isPro"],
        "token": token,
        "orgs": whoami["orgs"],
        "whoami": {k: v for k, v in whoami.items() if k not in WHOAMI_IDENTITY},
    }


@cache
def recorded_whoami(persona: str) -> dict:
    record = {"owner": "whoami-owner", "requester": "whoami-requester"}[persona]
    return copy.deepcopy(_seed_reads()[record]["body_json"])


def base_users(with_carol: bool = True) -> list[dict]:
    users = [
        _user_from_whoami(recorded_whoami("owner"), OWNER_EMAIL, "persona-owner"),
        _user_from_whoami(recorded_whoami("requester"), REQUESTER_EMAIL, "persona-requester"),
    ]
    if with_carol:
        # Clone-only third user (docs/system.md "Built-in seeds"); values are ours, not HF's.
        users.append({
            "user": CAROL, "_id": "64b0c0ffee00000000000c01", "fullname": "Demo Carol", "email": CAROL_EMAIL,
            "avatarUrl": "/avatars/democarol.svg", "isPro": False, "token": "persona-carol", "orgs": [],
            "whoami": {"emailVerified": True, "canPay": False, "billingMode": "prepaid", "periodEnd": None,
                       "auth": {"type": "access_token",
                                "accessToken": {"displayName": "conformance", "role": "write",
                                                "createdAt": "2026-10-01T00:00:00.000Z"}}},
        })
    return users


@cache
def sandbox_repo() -> dict:
    records = _seed_reads()
    info = copy.deepcopy(records["model-info-anon"]["body_json"])
    repo = {key: info.pop(key) for key in REPO_KEYS}
    siblings = info.pop("siblings")
    repo["gatedNotificationsMode"] = "bulk"  # API default unknown (Q-12); not observable (CFG-3)
    repo["gatedNotificationsEmail"] = None
    repo["orgMembersGated"] = False
    tree = [entry for record in ("tree-main", "tree-subdir") for entry in records[record]["body_json"]]
    listed = {entry["path"]: entry for entry in tree if entry["type"] == "file"}
    texts = {}
    for record in records.values():
        if "body_text" in record and record["status"] == 200:
            path = record["url"].split("/resolve/main/", 1)[1]
            texts[path] = record["body_text"]
    files = {}
    for sibling in siblings:
        path = sibling["rfilename"]
        entry = listed.get(path)
        # Files only known by name (siblings) stay empty: no size or oid is invented for them.
        file = {"oid": entry["oid"], "size": entry["size"]} if entry else {}
        if entry and "lfs" in entry:
            file["lfs"] = lfs_pointer(path, entry)
            file["xetHash"] = xet_hash(path)
        if path in texts:
            file["text"] = texts[path]
        files[path] = file
    repo["info"] = info
    # Directory oids (tree listing) are not implied by file paths; the clone's seed format carries them
    # under `dirs` (key name seen through GET /__clone__/state, values from tree-main).
    repo["dirs"] = {entry["path"]: {"oid": entry["oid"]} for entry in tree if entry["type"] == "directory"}
    repo["files"] = files
    return repo


# The one LFS file the recordings describe: the anonymous tree masks its sha256 and xetHash
# ("****…"), the owner's HEAD reveals them (`owner-head-lfs`: X-Linked-Etag, CDN path). The seed holds
# the real values; whether anonymous listings mask them is the backend's job.
LFS_FILE = "checkpoint_tokens_20M_loss_4.9842/pytorch_model.bin"


def _owner_head_lfs() -> dict:
    return _seed_reads()["owner-head-lfs"]["headers"]


def lfs_pointer(path: str, entry: dict) -> dict:
    assert path == LFS_FILE, path
    sha256 = _owner_head_lfs()["x-linked-etag"].strip('"')
    return {"oid": sha256, "size": entry["lfs"]["size"], "pointerSize": entry["lfs"]["pointerSize"]}


def xet_hash(path: str) -> str:
    assert path == LFS_FILE, path
    # Link: <…/v1/reconstructions/{xet hash}>; rel="xet-reconstruction-info"
    match = re.search(r"/v1/reconstructions/([0-9a-f]{64})>", _owner_head_lfs()["link"])
    assert match, _owner_head_lfs()["link"]
    return match.group(1)


def _stub_repo(repo_id: str, _id: str, gated: Any, files: dict[str, str], card: dict | None = None) -> dict:
    author = repo_id.split("/")[0]
    return {
        "id": repo_id, "_id": _id, "author": author, "private": False, "gated": gated,
        "orgMembersGated": False, "gatedNotificationsMode": "bulk", "gatedNotificationsEmail": None,
        "sha": hashlib.sha1(f"conformance-standin:{repo_id}".encode()).hexdigest(),
        "createdAt": "2024-01-01T00:00:00.000Z", "lastModified": "2024-01-01T00:00:00.000Z",
        "cardData": card or {}, "info": {},
        "files": {path: {"text": text, "oid": hashlib.sha1(text.encode()).hexdigest(), "size": len(text.encode())}
                  for path, text in files.items()},
    }


def _excerpt(record_id: str) -> str:
    return _records("2026-10-05-anonymous-probes.json")[record_id]["body_excerpt"]


def _meta_id(record_id: str) -> str:
    return json.loads(_excerpt(record_id))["_id"]


def standin_repos() -> list[dict]:
    """Local stand-ins for the real repos the anonymous probes hit. Not the real repos: contents are stubs."""
    anon = _records("2026-10-05-anonymous-probes.json")
    llama_props = anon["gate-props-manual-custom"]["props"]
    starcoder_props = anon["gate-props-auto"]["props"]
    stub = "stand-in content\n"
    return [
        _stub_repo(
            "meta-llama/Llama-3.2-1B", _meta_id("meta-manual"), "manual",
            {
                "README.md": _excerpt("allow-readme"),
                "LICENSE.txt": _excerpt("allow-license-txt"),
                "USE_POLICY.md": stub, "config.json": stub, ".gitattributes": stub,
                "original/params.json": stub,
            },
            {"extra_gated_fields": llama_props["additionalFields"],
             "extra_gated_button_content": llama_props["accessButtonString"]},
        ),
        _stub_repo(
            "bigcode/starcoder", _meta_id("meta-auto"), "auto",
            {"README.md": _excerpt("allow-readme-auto"), "config.json": stub},
            {"extra_gated_fields": starcoder_props["additionalFields"]},
        ),
        _stub_repo(
            "mistralai/Mistral-7B-v0.1", _meta_id("meta-not-gated"), False,
            {"README.md": stub, "config.json": stub},
            {"extra_gated_description": "stand-in stale description (CFG-5)"},
        ),
        _stub_repo("openai-community/gpt2", "64b0c0ffee0000000000a002", False, {"README.md": stub, "config.json": stub}),
    ]


def request(user: str, status: str, timestamp: str, reviewed_at: str | None = None,
            granted_by: str | None = None, fields: dict | None = None, email_shared: bool = True,
            repo: str = SANDBOX) -> dict:
    return {
        "repo": repo, "user": user, "status": status, "timestamp": timestamp, "reviewedAt": reviewed_at,
        "grantedBy": granted_by, "fields": fields, "emailShared": email_shared,
    }


def seed(name: str, now: str, requests: list[dict], repos: list[dict] | None = None,
         with_carol: bool = True, tick_ms: int = 1000) -> dict:
    return {
        "seed": name,
        "now": now,
        "tick_ms": tick_ms,
        "users": base_users(with_carol),
        "repos": repos if repos is not None else [copy.deepcopy(sandbox_repo())],
        "requests": requests,
    }


def _first_sent_at(file_name: str) -> str:
    data = json.loads((OBSERVATIONS / file_name).read_text())
    if isinstance(data, list):
        return data[0]["started_at"]
    return data["records"][0]["sent_at"]


def pinned_timestamps(document: dict) -> set[str]:
    """Every ISO timestamp the seed contains (they must come back verbatim)."""
    from .compare import ISO_TS

    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key != "now":
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str) and ISO_TS.match(node):
            found.add(node)

    walk(document)
    return found


# Initial request state of each recording, read off its first steps (and the previous recording).
def scenario_seed(scenario: str) -> dict:
    if scenario == "owner-walkthrough":
        # s0: all four lists empty, requester "not in the authorized list". The pending request seen
        # at 13:57 had been cancelled by hand on huggingface.co, outside the bridge (sources.md): replayed as "no request".
        return seed("conformance:owner-walkthrough", _first_sent_at("2026-10-05-owner-walkthrough.json"), [])
    if scenario == "owner-walkthrough-completion":
        # m0: TestingBOrig pending since 14:17:07.311Z (= owner-walkthrough s5b/s11).
        return seed(
            "conformance:owner-walkthrough-completion",
            _first_sent_at("2026-10-05-owner-walkthrough-completion.json"),
            [request("TestingBOrig", "pending", "2026-10-05T14:17:07.311Z")],
        )
    if scenario == "requester-ask-access":
        # pre-auth-check: no request. The recording has no sent_at; the clock starts before the
        # first ask-access (13:31:55.250Z per owner-reads).
        return seed("conformance:requester-ask-access", "2026-10-05T13:31:00.000Z", [])
    if scenario == "owner-reads":
        # owner-list-pending / owner-report: TestingBOrig pending since 13:31:55.250Z.
        return seed(
            "conformance:owner-reads", _first_sent_at("2026-10-05-owner-reads.json"),
            [request("TestingBOrig", "pending", "2026-10-05T13:31:55.250Z")],
        )
    if scenario == "clone-seed-reads":
        # Recorded at 14:31, after the UI walkthrough left TestingBOrig pending (UI #252). Also probes
        # openai-community/gpt2 (stand-in) and a missing repo (not seeded).
        repos = [copy.deepcopy(sandbox_repo()), *[r for r in standin_repos() if r["id"] == "openai-community/gpt2"]]
        return seed(
            "conformance:clone-seed-reads", _first_sent_at("2026-10-05-clone-seed-reads.json"),
            [request("TestingBOrig", "pending", "2026-10-05T14:20:42.886Z")], repos,
        )
    if scenario == "ui-walkthrough":
        # #193: "has been reset"; the reset entry is completion m8's (timestamp kept, reviewedAt = reset).
        return seed(
            "conformance:ui-walkthrough", _first_sent_at("2026-10-05-ui-walkthrough.json"),
            [request("TestingBOrig", "reset", "2026-10-05T14:17:07.311Z", "2026-10-05T14:19:22.565Z")],
        )
    if scenario == "tree-masking":
        # Recorded at 15:08 with the requester still pending ("requester (pending, no access)",
        # raw-readme-requester "awaiting a review"): the pending request left by the UI walkthrough (#252).
        return seed(
            "conformance:tree-masking", _first_sent_at("2026-10-05-tree-masking.json"),
            [request("TestingBOrig", "pending", "2026-10-05T14:20:42.886Z")],
        )
    if scenario == "anonymous-probes":
        # Recorded at 13:33 without sent_at; only repos matter (anonymous, no requests).
        return seed("conformance:anonymous-probes", "2026-10-05T13:33:00.000Z", [],
                    [copy.deepcopy(sandbox_repo()), *standin_repos()])
    raise KeyError(scenario)


SCENARIO_NAMES = (
    "owner-walkthrough",
    "owner-walkthrough-completion",
    "requester-ask-access",
    "owner-reads",
    "clone-seed-reads",
    "ui-walkthrough",
    "anonymous-probes",
    "tree-masking",
)
