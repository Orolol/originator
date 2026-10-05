"""In-memory state: seed load/dump, virtual clock, id counter, outbox and exchange log.

Nothing is written to disk (AGENTS.md hard rule 2); built-in seeds are read-only package data.
Determinism (docs/system.md "Clone: contract"): the clock starts at the seed's `now` and only
moves when a request changes state (by `tick_ms`, before stamping) or through
`/__clone__/clock`; ids come from a counter; lists keep a stable order.
"""

from __future__ import annotations

import copy
import itertools
import json
from collections import deque
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from importlib import resources
from typing import Any

from .domain import AccessRequest, Email
from .files import RepoFiles

DEFAULT_SEED = "sandbox"
SEED_STATUSES = ("pending", "accepted", "rejected", "reset")
LOG_MAX_ENTRIES = 1000  # same cap as the bridge's exchange log


class SeedError(ValueError):
    pass


def builtin_seed_names() -> list[str]:
    return sorted(p.name.removesuffix(".json") for p in resources.files("clone.seeds").iterdir()
                  if p.name.endswith(".json"))


def builtin_seed(name: str) -> dict:
    if name not in builtin_seed_names():
        raise SeedError(f"Unknown seed: {name}")
    return json.loads(resources.files("clone.seeds").joinpath(f"{name}.json").read_text())


EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
MS = timedelta(milliseconds=1)


def parse_iso(value: str) -> int:
    """ISO 8601 (`…Z` or an offset) → epoch milliseconds (integer arithmetic, sub-ms truncated)."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"timestamp without a time zone: {value!r}")
    return (dt - EPOCH) // MS


def format_iso(ms: int) -> str:
    """Epoch ms → `2026-10-05T14:20:42.886Z`, the Hub's format [OBS]."""
    return (EPOCH + ms * MS).isoformat(timespec="milliseconds").removesuffix("+00:00") + "Z"


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise SeedError(message)


class Store:
    def __init__(self, seed: dict | None = None):
        self.load(seed if seed is not None else builtin_seed(DEFAULT_SEED))

    # --- seed load / dump ---------------------------------------------------------------------

    def load(self, doc: dict) -> None:
        """Replace the whole state with a seed document; clears log and outbox. Validates first,
        so a rejected document leaves the current state untouched."""
        _require(isinstance(doc, dict), "seed must be a JSON object")
        doc = copy.deepcopy(doc)
        for key in ("now", "users", "repos", "requests"):
            _require(key in doc, f"seed is missing {key!r}")
        try:
            now_ms = parse_iso(doc["now"])
        except (TypeError, ValueError) as exc:
            raise SeedError(f"invalid now: {exc}") from None
        tick_ms = doc.get("tick_ms", 1000)
        _require(isinstance(tick_ms, int) and tick_ms >= 0, "tick_ms must be a non-negative integer")

        users: dict[str, dict] = {}
        for u in doc["users"]:
            for key in ("user", "_id", "fullname", "email", "avatarUrl", "isPro", "token"):
                _require(key in u, f"user is missing {key!r}: {u.get('user')!r}")
            _require(u["user"] not in users, f"duplicate user {u['user']!r}")
            users[u["user"]] = u
        tokens = [u["token"] for u in users.values()]
        _require(len(set(tokens)) == len(tokens), "duplicate user token")

        repos: dict[str, dict] = {}
        files: dict[str, RepoFiles] = {}
        for r in doc["repos"]:
            for key in ("id", "_id", "author", "gated", "sha"):
                _require(key in r, f"repo is missing {key!r}: {r.get('id')!r}")
            _require(r["gated"] in (False, "auto", "manual"), f"invalid gated for {r['id']!r}")
            _require(r["id"] not in repos, f"duplicate repo {r['id']!r}")
            repos[r["id"]] = r
            files[r["id"]] = RepoFiles(r["id"], r.get("files", {}), r.get("dirs"))

        requests: dict[tuple[str, str], AccessRequest] = {}
        for q in doc["requests"]:
            _require(q.get("repo") in repos, f"request on unknown repo {q.get('repo')!r}")
            _require(q.get("user") in users, f"request by unknown user {q.get('user')!r}")
            _require(q.get("status") in SEED_STATUSES, f"invalid request status {q.get('status')!r}")
            _require((q["repo"], q["user"]) not in requests, "two requests for the same (repo, user)")
            _require(q.get("grantedBy") in (None, *users), f"grantedBy is not a user: {q.get('grantedBy')!r}")
            try:
                parse_iso(q["timestamp"])
            except (KeyError, TypeError, ValueError):
                raise SeedError(f"invalid request timestamp for {q['user']!r}") from None
            requests[(q["repo"], q["user"])] = AccessRequest(
                repo=q["repo"], user=q["user"], status=q["status"], timestamp=q["timestamp"],
                reviewedAt=q.get("reviewedAt"), grantedBy=q.get("grantedBy"), fields=q.get("fields"),
                emailShared=q.get("emailShared", True),
            )

        self.seed_name = doc.get("seed", "custom")
        self.now_ms, self.tick_ms = now_ms, tick_ms
        self.users = users
        self.users_by_token = {u["token"]: u for u in users.values()}
        self.users_by_id = {u["_id"].lower(): u for u in users.values()}
        self.repos, self.files, self.requests = repos, files, requests
        self._ids = itertools.count(1)
        self._log_ids = itertools.count(1)
        self.outbox: list[dict] = []
        self.log: deque[dict] = deque(maxlen=LOG_MAX_ENTRIES)

    def dump(self) -> dict:
        """The full state in the seed format (round-trips with `load`)."""
        return copy.deepcopy({
            "seed": self.seed_name,
            "now": format_iso(self.now_ms),
            "tick_ms": self.tick_ms,
            "users": list(self.users.values()),
            "repos": list(self.repos.values()),
            "requests": [asdict(r) for r in self.requests.values()],
        })

    # --- clock and ids ------------------------------------------------------------------------

    @property
    def now(self) -> str:
        return format_iso(self.now_ms)

    def next_stamp(self) -> int:
        """The time a state change made now would be stamped with (clock + tick_ms)."""
        return self.now_ms + self.tick_ms

    def commit_stamp(self, stamp_ms: int) -> None:
        self.now_ms = stamp_ms

    def new_id(self) -> str:
        """24-hex ObjectId-like ids from a counter."""
        return f"{next(self._ids):024x}"

    # --- requests ------------------------------------------------------------------------------

    def get_request(self, repo_id: str, user: str) -> AccessRequest | None:
        return self.requests.get((repo_id, user))

    def put_request(self, repo_id: str, user: str, request: AccessRequest | None) -> None:
        key = (repo_id, user)
        if request is None:
            self.requests.pop(key, None)
        else:
            self.requests[key] = request  # an existing key keeps its insertion position

    def repo_requests(self, repo_id: str, status: str | None = None) -> list[AccessRequest]:
        """Stable order. Provisional (Q-10): `timestamp` ascending, then insertion order."""
        reqs = [r for (rid, _), r in self.requests.items() if rid == repo_id and (status is None or r.status == status)]
        return sorted(reqs, key=lambda r: parse_iso(r.timestamp))

    # --- outbox and log ------------------------------------------------------------------------

    def send_email(self, email: Email, *, at: str, to: str, repo: str, user: str) -> None:
        entry: dict[str, Any] = {"id": self.new_id(), "at": at, "to": to, "kind": email.kind,
                                 "repo": repo, "user": user}
        if email.reason is not None:
            entry["reason"] = email.reason
        self.outbox.append(entry)

    def record(self, **fields: Any) -> None:
        self.log.append({"id": next(self._log_ids), **fields})
