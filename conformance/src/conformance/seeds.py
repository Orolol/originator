"""Initial states (clone seed documents) written from the recordings, never from the clone.

Seed format: docs/system.md "Seed format". The recordings come in **sets**, one per day and sandbox:

- `2026-10-05`: sandbox `Orosius/deltanet-mla-latent`, owner `Orosius`;
- `2026-10-06`: sandbox `OwnerOfTheGatedModel/tiny-gated-model`, owner `OwnerOfTheGatedModel`.

The requester (`TestingBOrig`) is the same in both. Everything static (users, the sandbox repo, its
files) is derived programmatically from each set's `<date>-clone-seed-reads.json`, so a typo cannot
creep in:

- users: `whoami-owner` / `whoami-requester`;
- sandbox repo: `model-info-anon`, `tree-main`, `tree-subdir`, the `body_text` of small files, and the
  LFS sha256 / xet hash revealed by `owner-head-lfs`;
- stand-in repos (other real repos probed anonymously on 2026-10-05): ids, `_id` and `gated` from
  `2026-10-05-anonymous-probes.json`; file *contents* are stubs (the recorded 160-character excerpt),
  so only status, error headers and allowlist decisions are meaningful for them.

The request state at the start of each recording is written per scenario (`scenario_seed`) from what
the recording's first steps show (and the previous recording of the same set, in `sent_at` order).
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from functools import cache
from typing import Any

from .config import OBSERVATIONS

SETS = ("2026-10-05", "2026-10-06")  # recording sets, oldest first
LATEST = SETS[-1]  # the sandbox the bridge (live mode) and the rule tests target
REQUESTER_EMAIL = "testingborig@example.com"
CAROL = "DemoCarol"
CAROL_EMAIL = "carol@example.org"

# Top-level repo keys of the seed format; every other model-info field goes to `info`, verbatim.
REPO_KEYS = ("_id", "id", "author", "private", "gated", "sha", "createdAt", "lastModified", "cardData")


@cache
def _records(file_name: str) -> dict[str, dict]:
    data = json.loads((OBSERVATIONS / file_name).read_text())
    return {r["id"]: r for r in data["records"]}


def _seed_reads(rset: str) -> dict[str, dict]:
    return _records(f"{rset}-clone-seed-reads.json")


@dataclass(frozen=True)
class RecordingSet:
    date: str
    sandbox: str  # repo id, from model-info-anon
    owner: str  # from whoami-owner
    owner_email: str  # placeholder: recordings redact e-mails to <email>
    lfs_file: str  # the one LFS file of the sandbox, from the recorded tree

    @property
    def lfs_dir(self) -> str:
        return self.lfs_file.rsplit("/", 1)[0]


@cache
def recording_set(rset: str = LATEST) -> RecordingSet:
    records = _seed_reads(rset)
    sandbox = records["model-info-anon"]["body_json"]["id"]
    owner = records["whoami-owner"]["body_json"]["name"]
    tree = [entry for record in ("tree-main", "tree-subdir") for entry in records[record]["body_json"]]
    [lfs_file] = [entry["path"] for entry in tree if entry["type"] == "file" and "lfs" in entry]
    return RecordingSet(rset, sandbox, owner, f"{owner.lower()}@example.com", lfs_file)


# Shorthands for the latest set (rule tests, live mode).
SANDBOX = recording_set().sandbox
OWNER = recording_set().owner
OWNER_EMAIL = recording_set().owner_email
LFS_FILE = recording_set().lfs_file
LFS_DIR = recording_set().lfs_dir


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
def _recorded_whoami(persona: str, rset: str) -> dict:
    record = {"owner": "whoami-owner", "requester": "whoami-requester"}[persona]
    return _seed_reads(rset)[record]["body_json"]


def recorded_whoami(persona: str, rset: str = LATEST) -> dict:
    return copy.deepcopy(_recorded_whoami(persona, rset))


def base_users(with_carol: bool = True, rset: str = LATEST) -> list[dict]:
    users = [
        _user_from_whoami(recorded_whoami("owner", rset), recording_set(rset).owner_email, "persona-owner"),
        _user_from_whoami(recorded_whoami("requester", rset), REQUESTER_EMAIL, "persona-requester"),
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
def _sandbox_repo(rset: str) -> dict:
    records = _seed_reads(rset)
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
        if "body_text" in record and record["status"] == 200 and "/resolve/main/" in record["url"]:
            path = record["url"].split("/resolve/main/", 1)[1]
            texts[path] = record["body_text"]
    files = {}
    for sibling in siblings:
        path = sibling["rfilename"]
        entry = listed.get(path)
        # Files only known by name (siblings) stay empty: no size or oid is invented for them.
        file = {"oid": entry["oid"], "size": entry["size"]} if entry else {}
        if entry and "lfs" in entry:
            file["lfs"] = lfs_pointer(path, entry, rset)
            file["xetHash"] = xet_hash(path, rset)
        if path in texts:
            file["text"] = texts[path]
        files[path] = file
    repo["info"] = info
    # Directory oids (tree listing) are not implied by file paths; the clone's seed format carries them
    # under `dirs` (key name seen through GET /__clone__/state, values from tree-main).
    repo["dirs"] = {entry["path"]: {"oid": entry["oid"]} for entry in tree if entry["type"] == "directory"}
    repo["files"] = files
    return repo


def sandbox_repo(rset: str = LATEST) -> dict:
    return copy.deepcopy(_sandbox_repo(rset))


# The one LFS file each set describes: the anonymous tree masks its sha256 and xetHash ("****…"), the
# owner's HEAD reveals them (`owner-head-lfs`: X-Linked-Etag, xet Link). The seed holds the real values;
# whether anonymous listings mask them is the backend's job.
def _owner_head_lfs(rset: str) -> dict:
    return _seed_reads(rset)["owner-head-lfs"]["headers"]


def lfs_pointer(path: str, entry: dict, rset: str = LATEST) -> dict:
    assert path == recording_set(rset).lfs_file, path
    sha256 = _owner_head_lfs(rset)["x-linked-etag"].strip('"')
    return {"oid": sha256, "size": entry["lfs"]["size"], "pointerSize": entry["lfs"]["pointerSize"]}


def xet_hash(path: str, rset: str = LATEST) -> str:
    assert path == recording_set(rset).lfs_file, path
    # Link: <…/v1/reconstructions/{xet hash}>; rel="xet-reconstruction-info"
    match = re.search(r"/v1/reconstructions/([0-9a-f]{64})>", _owner_head_lfs(rset)["link"])
    assert match, _owner_head_lfs(rset)["link"]
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
         with_carol: bool = True, tick_ms: int = 1000, rset: str = LATEST) -> dict:
    return {
        "seed": name,
        "now": now,
        "tick_ms": tick_ms,
        "users": base_users(with_carol, rset),
        "repos": repos if repos is not None else [sandbox_repo(rset)],
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


# Initial request state of each recording, read off its first steps (and the previous recording of the
# same set in `sent_at` order). Scenario names are "<set>/<recording>", e.g. "2026-10-06/owner-walkthrough".
def scenario_seed(scenario: str) -> dict:
    rset, name = scenario.split("/", 1)
    if rset == "2026-10-05":
        return _seed_2026_10_05(scenario, name)
    if rset == "2026-10-06":
        return _seed_2026_10_06(scenario, name)
    raise KeyError(scenario)


def _seed_2026_10_05(scenario: str, name: str) -> dict:
    rset = "2026-10-05"
    sandbox = recording_set(rset).sandbox
    first = lambda: _first_sent_at(f"{rset}-{name}.json")  # noqa: E731

    def pending(timestamp: str) -> dict:
        return request("TestingBOrig", "pending", timestamp, repo=sandbox)

    def make(now: str, requests: list[dict], repos: list[dict] | None = None) -> dict:
        return seed(f"conformance:{scenario}", now, requests, repos, rset=rset)

    if name == "owner-walkthrough":
        # s0: all four lists empty, requester "not in the authorized list". The pending request seen
        # at 13:57 had been cancelled by hand on huggingface.co, outside the bridge (sources.md): replayed as "no request".
        return make(first(), [])
    if name == "owner-walkthrough-completion":
        # m0: TestingBOrig pending since 14:17:07.311Z (= owner-walkthrough s5b/s11).
        return make(first(), [pending("2026-10-05T14:17:07.311Z")])
    if name == "requester-ask-access":
        # pre-auth-check: no request. The recording has no sent_at; the clock starts before the
        # first ask-access (13:31:55.250Z per owner-reads).
        return make("2026-10-05T13:31:00.000Z", [])
    if name == "owner-reads":
        # owner-list-pending / owner-report: TestingBOrig pending since 13:31:55.250Z.
        return make(first(), [pending("2026-10-05T13:31:55.250Z")])
    if name == "clone-seed-reads":
        # Recorded at 14:31, after the UI walkthrough left TestingBOrig pending (UI #252). Also probes
        # openai-community/gpt2 (stand-in) and a missing repo (not seeded).
        repos = [sandbox_repo(rset), *[r for r in standin_repos() if r["id"] == "openai-community/gpt2"]]
        return make(first(), [pending("2026-10-05T14:20:42.886Z")], repos)
    if name == "ui-walkthrough":
        # #193: "has been reset"; the reset entry is completion m8's (timestamp kept, reviewedAt = reset).
        return make(first(), [request("TestingBOrig", "reset", "2026-10-05T14:17:07.311Z", "2026-10-05T14:19:22.565Z",
                                      repo=sandbox)])
    if name == "tree-masking":
        # Recorded at 15:08 with the requester still pending ("requester (pending, no access)",
        # raw-readme-requester "awaiting a review"): the pending request left by the UI walkthrough (#252).
        return make(first(), [pending("2026-10-05T14:20:42.886Z")])
    if name == "anonymous-probes":
        # Recorded at 13:33 without sent_at; only repos matter (anonymous, no requests).
        return make("2026-10-05T13:33:00.000Z", [], [sandbox_repo(rset), *standin_repos()])
    raise KeyError(scenario)


def _seed_2026_10_06(scenario: str, name: str) -> dict:
    # Time order (sent_at): clone-seed-reads 13:49:13 -> requester-ask-access 13:49:33 -> owner-reads 13:49:42
    # -> tree-masking 13:49:44 -> owner-walkthrough 13:50:04 -> owner-walkthrough-completion 13:50:41
    # -> requester-cancel 13:51:09 -> (the live spec puts the request in `reset`, clears the log) -> ui-walkthrough 14:01:49.
    rset = "2026-10-06"
    sandbox = recording_set(rset).sandbox
    first = _first_sent_at(f"{rset}-{name}.json")

    def make(requests: list[dict], repos: list[dict] | None = None) -> dict:
        return seed(f"conformance:{scenario}", first, requests, repos, rset=rset)

    # The request created by requester-ask-access `ask-access-json` (owner-reads owner-list-pending timestamp).
    first_ask = request("TestingBOrig", "pending", "2026-10-06T13:49:34.895Z", repo=sandbox)
    if name == "clone-seed-reads":
        # No request yet: the next recording (requester-ask-access pre-auth-check, 13:49:33) still answers
        # "not in the authorized list". Also probes openai-community/gpt2 (owner-not-gated-list, stand-in)
        # and a missing repo (not seeded).
        repos = [sandbox_repo(rset), *[r for r in standin_repos() if r["id"] == "openai-community/gpt2"]]
        return make([], repos)
    if name == "requester-ask-access":
        # pre-auth-check / pre-resolve: "restricted and you are not in the authorized list" -> no request.
        return make([])
    if name == "owner-reads":
        # owner-list-pending / owner-report: TestingBOrig pending since 13:49:34.895Z (ask-access-json).
        return make([first_ask])
    if name == "tree-masking":
        # raw-readme-requester "awaiting a review": still the pending request seen by owner-reads.
        return make([first_ask])
    if name == "owner-walkthrough":
        # s0-list-pending: TestingBOrig pending since 13:49:34.895Z; the three other lists empty.
        return make([first_ask])
    if name == "owner-walkthrough-completion":
        # m0-list-pending: pending since 13:50:22.677Z (= owner-walkthrough s5b re-request, s11-report time).
        return make([request("TestingBOrig", "pending", "2026-10-06T13:50:22.677Z", repo=sandbox)])
    if name == "requester-cancel":
        # c0-list-reset: reset, timestamp 13:50:22.677Z, reviewedAt 13:50:54.253Z (= completion m8 reset).
        return make([request("TestingBOrig", "reset", "2026-10-06T13:50:22.677Z", "2026-10-06T13:50:54.253Z",
                             repo=sandbox)])
    if name == "ui-walkthrough":
        # #315: "has been reset" (web/e2e/live-walkthrough.spec.ts puts the request in `reset` and clears the
        # log before the journey). The reset entry's timestamp/reviewedAt are not visible in any replayed step:
        # #316 re-requests (new timestamp, reviewedAt removed) before the first owner list. Values below are
        # the last recorded request (requester-cancel c5-list-rejected timestamp) and a reviewedAt before the
        # journey; neither is compared.
        return make([request("TestingBOrig", "reset", "2026-10-06T13:51:15.900Z", "2026-10-06T14:00:00.000Z",
                             repo=sandbox)])
    raise KeyError(scenario)


SCENARIO_NAMES = (
    "2026-10-05/owner-walkthrough",
    "2026-10-05/owner-walkthrough-completion",
    "2026-10-05/requester-ask-access",
    "2026-10-05/owner-reads",
    "2026-10-05/clone-seed-reads",
    "2026-10-05/ui-walkthrough",
    "2026-10-05/anonymous-probes",
    "2026-10-05/tree-masking",
    "2026-10-06/clone-seed-reads",
    "2026-10-06/requester-ask-access",
    "2026-10-06/owner-reads",
    "2026-10-06/tree-masking",
    "2026-10-06/owner-walkthrough",
    "2026-10-06/owner-walkthrough-completion",
    "2026-10-06/requester-cancel",
    "2026-10-06/ui-walkthrough",
)
