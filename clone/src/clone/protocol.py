"""HTTP layer: HF's wire protocol for the slice (docs/hf-gated/api.md, docs/system.md "Backend
surface"), mapped onto the domain and the store.

Response conventions [OBS, docs/hf-gated/observations/]:
- JSON bodies are compact (`JSON.stringify`); `Content-Type: application/json; charset=utf-8`.
- Every non-redirect body carries Express's weak ETag `W/"<len hex>-<sha1 base64[:27]>"`
  (recomputed and matched on every recorded body); resolved files carry `"<git oid>"` instead.
- Errors: `X-Error-Message` (+ `X-Error-Code` only where HF sends one); JSON `{"error"}` under
  /api, `text/plain` on resolve, HTML on the other web routes; 401s add `WWW-Authenticate`.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode

from starlette.responses import Response, StreamingResponse

from . import domain
from .domain import AccessRequest, AlreadyHasAccess, Change, RequestNotFound
from .files import content_chunks, lfs_pointer
from .store import Store, format_iso, parse_iso
from .zod import MISSING, Checker, Issue, ValidationFailed, check_user_ref, header_safe, refine_user_ref

JSON_TYPE = "application/json; charset=utf-8"
TEXT_TYPE = "text/plain; charset=utf-8"
HTML_TYPE = "text/html; charset=utf-8"

# Messages, verbatim [OBS 2026-10-05] (api.md §3).
INVALID_CREDENTIALS = "Invalid username or password."
WWW_AUTHENTICATE = 'Bearer realm="Authentication required", charset="UTF-8"'
REPO_NOT_FOUND = "Repository not found"
NO_PERMISSION = "You have read access but not the required permissions for this operation"
USER_NOT_FOUND = "User not found"
REQUEST_NOT_FOUND = "No access request found matching your criteria"
NO_PENDING_REQUEST = "No pending access request found for this repo and this user"  # REQ-7
ALREADY_HAS_ACCESS = "That user already has access to the repo"


def repo_not_gated(repo: dict) -> HttpError:
    """REV-7 [OBS 2026-10-06 edge-cases-b e12-grant-not-gated, e12-handle-not-gated]."""
    return HttpError(error(400, f"model {repo['id']} is not gated", Fmt.API, "RepoNotGated"))
PAGE_NOT_FOUND = "Sorry, we can't find the page you are looking for."
ENTRY_NOT_FOUND = "Entry not found"
# Provisional: the RevisionNotFound wording was never recorded (ACC-6 only shows the gate wins).
REVISION_NOT_FOUND = "Revision not found"

STREAM_ABOVE = 8 << 20  # stub files bigger than this are streamed

# The ISO date-time pattern of the list query (`after`/`before`) in HF's OpenAPI spec.
ISO_DATETIME = re.compile(
    r"^(?:(?:\d\d[2468][048]|\d\d[13579][26]|\d\d0[48]|[02468][048]00|[13579][26]00)-02-29|\d{4}-"
    r"(?:(?:0[13578]|1[02])-(?:0[1-9]|[12]\d|3[01])|(?:0[469]|11)-(?:0[1-9]|[12]\d|30)|(?:02)-"
    r"(?:0[1-9]|1\d|2[0-8])))T(?:(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z))$"
)
# gatedNotificationsEmail pattern from the settings schema (snapshots/openapi-gated.json).
EMAIL = re.compile(r"^(?!\.)(?!.*\.\.)([A-Za-z0-9_'+\-\.]*)[A-Za-z0-9_+-]@([A-Za-z0-9][A-Za-z0-9\-]*\.)+[A-Za-z]{2,}$")


class Fmt(Enum):
    API = "api"  # JSON {"error"}
    PLAIN = "plain"  # text/plain (resolve) [OBS]
    HTML = "html"  # other web routes: HF renders an HTML page [OBS report-anon, anon-ask-access-get]


def dumps(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()


def weak_etag(body: bytes) -> str:
    return 'W/"%x-%s"' % (len(body), base64.b64encode(hashlib.sha1(body).digest()).decode()[:27])


def respond(status: int, body: bytes, content_type: str, headers: dict[str, str] | None = None,
            *, etag: bool = True) -> Response:
    h = {"Content-Type": content_type, **(headers or {})}
    if etag and "ETag" not in h:
        h["ETag"] = weak_etag(body)
    return Response(content=body, status_code=status, headers=h)


def json_ok(obj: Any, headers: dict[str, str] | None = None) -> Response:
    return respond(200, dumps(obj), JSON_TYPE, headers)


def error(status: int, message: str, fmt: Fmt, code: str | None = None, *,
          www_authenticate: bool = True) -> Response:
    headers = {"X-Error-Message": header_safe(message)}
    if code:
        headers["X-Error-Code"] = code
    if status == 401 and www_authenticate:
        headers["WWW-Authenticate"] = WWW_AUTHENTICATE
    if fmt is Fmt.API:
        return respond(status, dumps({"error": message}), JSON_TYPE, headers)
    if fmt is Fmt.PLAIN:
        return respond(status, message.encode(), TEXT_TYPE, headers)
    # Provisional: the message instead of HF's full HTML error page (behaviour, not pixels).
    return respond(status, html.escape(message).encode(), HTML_TYPE, headers)


def redirect(status: int, location: str, reason: str, body_target: str | None = None,
             headers: dict[str, str] | None = None) -> Response:
    """Express-style redirect body `<reason>. Redirecting to <url>` [OBS 303, 307, 302]; no ETag
    [OBS 303 (UI #194), 302 (owner-head-lfs)]; Provisional for the 307."""
    body = f"{reason}. Redirecting to {body_target or location}".encode()
    return respond(status, body, TEXT_TYPE, {"Location": location, **(headers or {})}, etag=False)


class HttpError(Exception):
    def __init__(self, response: Response):
        self.response = response


@dataclass
class Ctx:
    store: Store
    public_url: str
    method: str
    path: str
    caller: dict | None  # seed user, None = anonymous (or an invalid token)
    invalid_token: bool
    query: list[tuple[str, str]]
    body: bytes
    content_type: str | None

    @property
    def username(self) -> str | None:
        return self.caller["user"] if self.caller else None

    def param(self, name: str) -> str | None:
        return next((v for k, v in self.query if k == name), None)

    def params(self, *names: str) -> list[str]:
        return [v for k, v in self.query if k in names]


def identify(store: Store, authorization: str | None) -> tuple[str, dict | None]:
    """(persona for the log, caller). Persona names follow the bridge's (`owner`, `requester`,
    `anonymous`, `invalid`); a seeded token `persona-x` is persona `x`."""
    if authorization is None:
        return "anonymous", None
    scheme, _, token = authorization.partition(" ")
    user = store.users_by_token.get(token.strip()) if scheme.lower() == "bearer" else None
    if user is None:
        return "invalid", None
    return user["token"].removeprefix("persona-") if user["token"].startswith("persona-") else user["user"], user


# --- shared checks ---------------------------------------------------------------------------------


def visible_repo(ctx: Ctx, repo_id: str, fmt: Fmt) -> dict:
    repo = ctx.store.repos.get(repo_id)
    # Provisional (CFG-4): a private repo is hidden from everyone but its owner, like a missing one.
    if repo is None or (repo.get("private") and ctx.username != repo["author"]):
        if ctx.caller is None:
            # Unknown repo, anonymous → 401 without code [OBS missing-repo-resolve, auth-check-missing]
            raise HttpError(error(401, INVALID_CREDENTIALS, fmt))
        # Logged in → 404 RepoNotFound [OBS owner-unknown-repo-list]
        raise HttpError(error(404, REPO_NOT_FOUND, fmt, "RepoNotFound"))
    return repo


def owner_repo(ctx: Ctx, repo_id: str, fmt: Fmt) -> dict:
    """Owner-endpoint check order (api.md §3.3): authentication, repo, then write permission."""
    if ctx.caller is None:
        raise HttpError(error(401, INVALID_CREDENTIALS, fmt))  # [OBS owner-list-anon, report-anon]
    repo = visible_repo(ctx, repo_id, fmt)
    if ctx.username != repo["author"]:
        # [OBS W s7-req-handle, owner-not-gated-list]: no X-Error-Code. Only the user-namespace
        # owner has write access here (orgs are not modelled).
        raise HttpError(error(403, NO_PERMISSION, fmt))
    return repo


def api_body(ctx: Ctx) -> Any:
    """JSON body of an /api call. Provisional (Q-9): an empty body is `{}`, a malformed one is
    reported like a missing object (zod's "expected object, received undefined")."""
    if not ctx.body.strip():
        return {}
    try:
        return json.loads(ctx.body)
    except ValueError:
        return MISSING


def validate(check: Callable[[Checker], None]) -> None:
    c = Checker()
    check(c)
    c.raise_if_any()


def find_user(store: Store, ref: dict) -> dict | None:
    """REV-5: by username (`user`) or by 24-hex `_id` (`userId`) [OBS C m3]."""
    if "user" in ref:
        return store.users.get(ref["user"])
    return store.users_by_id.get(ref["userId"].lower())


def commit(ctx: Ctx, repo: dict, user: str, change: Change, stamp_ms: int) -> None:
    """Apply a domain change: advance the clock, store the request, queue its e-mails."""
    if not change.changed:
        return
    store = ctx.store
    store.commit_stamp(stamp_ms)
    store.put_request(repo["id"], user, change.request)
    for email in change.emails:
        if email.kind == "new_request":
            # §7: the notification recipient: gatedNotificationsEmail, else the owner's e-mail.
            owner = store.users.get(repo["author"])
            to = repo.get("gatedNotificationsEmail") or (owner["email"] if owner else None)
        else:
            to = store.users[user]["email"]  # REV-3: the reset e-mail goes to the requester
        store.send_email(email, at=format_iso(stamp_ms), to=to, repo=repo["id"], user=user)


def _short_user(u: dict) -> dict:
    return {"_id": u["_id"], "avatarUrl": u["avatarUrl"], "isPro": u["isPro"], "fullname": u["fullname"],
            "user": u["user"], "type": "user"}


def list_item(store: Store, req: AccessRequest) -> dict:
    """api.md §2 item. REQ-6 key order [OBS]: user, timestamp, reviewedAt, status, grantedBy."""
    u = store.users[req.user]
    user = {**_short_user(u), "verifiedOrgNames": []}
    if req.emailShared:
        user["email"] = u["email"]  # REQ-5: no email for users added through grant
    item: dict[str, Any] = {"user": user}
    if req.fields is not None:
        item["fields"] = req.fields  # Provisional (Q-13): position never observed
    item["timestamp"] = req.timestamp
    if req.reviewedAt is not None:
        item["reviewedAt"] = req.reviewedAt
    item["status"] = req.status
    if req.grantedBy is not None:
        item["grantedBy"] = _short_user(store.users[req.grantedBy])  # [OBS W s4]: no email/orgs
    return item


# --- public reads ---------------------------------------------------------------------------------


def whoami(ctx: Ctx) -> Response:
    if ctx.caller is None:
        raise HttpError(error(401, INVALID_CREDENTIALS, Fmt.API))  # [OBS whoami-anon]
    u = ctx.caller
    extra = u.get("whoami", {})
    body = {"type": "user", "id": u["_id"], "name": u["user"], "fullname": u["fullname"], "email": u["email"]}
    body |= {k: extra[k] for k in ("emailVerified", "canPay", "billingMode", "periodEnd") if k in extra}
    body |= {"isPro": u["isPro"], "avatarUrl": u["avatarUrl"], "orgs": u.get("orgs", [])}
    body |= {k: v for k, v in extra.items() if k not in body}  # `auth`, …  [OBS whoami-owner order]
    return json_ok(body)


def quicksearch(ctx: Ctx) -> Response:
    """Provisional (Q-25): HF's user search was never observed returning users. Users whose
    username or fullname starts with `q` (case-insensitive), in seed order, shaped like HF's
    OpenAPI quicksearch users; `type` other than `user` is a validation error ([OBS] for `users`)."""
    kind = ctx.param("type")
    if kind is not None and kind != "user":
        raise ValidationFailed([Issue("Invalid input", ("type",))])
    q = (ctx.param("q") or "").lower()
    users = [{"_id": u["_id"], "avatarUrl": u["avatarUrl"], "fullname": u["fullname"], "user": u["user"]}
             for u in ctx.store.users.values()
             if u["user"].lower().startswith(q) or u["fullname"].lower().startswith(q)]
    return json_ok({"users": users})


# [OBS model-info-anon] key order of the full model info.
MODEL_INFO_ORDER = ("_id", "id", "private", "tags", "downloads", "likes", "modelId", "author", "sha",
                    "lastModified", "gated", "disabled", "model-index", "config", "cardData", "siblings",
                    "spaces", "createdAt", "usedStorage")
REPO_LEVEL = ("_id", "id", "private", "author", "sha", "lastModified", "gated", "cardData", "createdAt")


def model_info(ctx: Ctx, ns: str, name: str) -> Response:
    """ACC-4: public on a gated repo; identical for every caller [OBS model-info-owner == anon].
    Notification settings are never exposed (CFG-3)."""
    repo = visible_repo(ctx, f"{ns}/{name}", Fmt.API)
    info = repo.get("info", {})
    full: dict[str, Any] = {}
    for key in MODEL_INFO_ORDER:
        if key == "siblings":
            full[key] = ctx.store.files[repo["id"]].siblings()
        elif key in REPO_LEVEL and key in repo:
            full[key] = repo[key]
        elif key in info:
            full[key] = info[key]
    full |= {k: v for k, v in info.items() if k not in full}
    expand = ctx.params("expand[]", "expand")
    if not expand:
        return json_ok(full)
    # [OBS model-info-expand]: `_id`, `id`, then the requested fields only.
    # Provisional: canonical key order; unknown names are skipped.
    return json_ok({k: v for k, v in full.items() if k in ("_id", "id") or k in expand})


def check_revision(repo: dict, rev: str, fmt: Fmt) -> None:
    # Provisional: the only refs are `main` and the head commit sha.
    if rev not in ("main", repo["sha"]):
        raise HttpError(error(404, REVISION_NOT_FOUND, fmt, "RevisionNotFound"))


def tree(ctx: Ctx, ns: str, name: str, rev: str, path: str | None) -> Response:
    """ACC-4: the tree listing is public. ACC-9 [OBS tree-masking]: the LFS sha256 and xet hash
    are masked for callers without access (the ACC-1 decision, no allowlist)."""
    repo = visible_repo(ctx, f"{ns}/{name}", Fmt.API)
    check_revision(repo, rev, Fmt.API)
    recursive = (ctx.param("recursive") or "").lower() in ("true", "1")
    entries = ctx.store.files[repo["id"]].tree((path or "").strip("/"), recursive=recursive,
                                               mask_lfs=denial(ctx, repo) is not None)
    if entries is None:
        raise HttpError(error(404, ENTRY_NOT_FOUND, Fmt.API, "EntryNotFound"))  # Provisional
    return json_ok(entries)


def denial(ctx: Ctx, repo: dict, path: str | None = None) -> domain.Denied | None:
    """The caller's access decision; `path` only for the ACC-5 allowlist (resolve)."""
    req = ctx.store.get_request(repo["id"], ctx.username) if ctx.caller else None
    return domain.check_access(repo_id=repo["id"], gated=repo["gated"], owner=repo["author"],
                               caller=ctx.username, request_status=req.status if req else None, path=path)


def gate(ctx: Ctx, repo: dict, fmt: Fmt, path: str | None = None) -> None:
    denied = denial(ctx, repo, path)
    if denied:
        raise HttpError(error(denied.status, denied.message, fmt, "GatedRepo"))


def auth_check(ctx: Ctx, ns: str, name: str) -> Response:
    repo = visible_repo(ctx, f"{ns}/{name}", Fmt.API)
    gate(ctx, repo, Fmt.API)  # same answer as resolve, but JSON [OBS]
    return respond(200, b"OK", TEXT_TYPE)


# --- file routes ------------------------------------------------------------------------------------


def file_response(ctx: Ctx, repo: dict, path: str, *, lfs_object: bool = False,
                  git_blob: bool = False) -> Response:
    """A file's bytes with the recorded resolve headers [OBS owner-readme, raw-readme-owner].
    `git_blob` (raw): an LFS file is served as its git blob, the LFS pointer (Provisional, no Q yet)."""
    meta = ctx.store.files[repo["id"]].files[path]
    if git_blob and meta.is_lfs:
        pointer = lfs_pointer(meta.lfs_oid, meta.size)
        return Response(content=pointer, headers=_file_headers(repo, path, meta.oid, len(pointer)))
    headers = _file_headers(repo, path, meta.lfs_oid if lfs_object else meta.oid, meta.size)
    if meta.size > STREAM_ABOVE:
        return StreamingResponse(content_chunks(repo["id"], meta), headers=headers)
    return Response(content=b"".join(content_chunks(repo["id"], meta)), headers=headers)


def _file_headers(repo: dict, path: str, etag: str, size: int) -> dict[str, str]:
    basename = path.rsplit("/", 1)[-1]
    # Provisional: non-ASCII characters of the plain `filename` (never recorded) become `?`.
    ascii_name = basename.encode("ascii", "replace").decode()
    headers = {
        "Content-Type": TEXT_TYPE,  # [OBS] every recorded file, JSON included, is text/plain
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(basename)}; filename=\"{ascii_name}\";",
        # The git oid [OBS]. Provisional: the LFS object behind the clone-local redirect is tagged
        # with its sha256 instead.
        "ETag": f'"{etag}"',
        "X-Repo-Commit": repo["sha"],
        "Content-Length": str(size),
    }
    return headers


def resolve(ctx: Ctx, ns: str, name: str, rev: str, path: str) -> Response:
    repo = visible_repo(ctx, f"{ns}/{name}", Fmt.PLAIN)
    gate(ctx, repo, Fmt.PLAIN, path)  # ACC-6: the gate comes before revision and file existence
    check_revision(repo, rev, Fmt.PLAIN)
    meta = ctx.store.files[repo["id"]].files.get(path)
    if meta is None:
        raise HttpError(error(404, ENTRY_NOT_FOUND, Fmt.PLAIN, "EntryNotFound"))  # [OBS allow-license-missing]
    cache_path = f"/api/resolve-cache/models/{repo['id']}/{repo['sha']}/{quote(path)}"
    if meta.is_lfs:
        # Provisional: HF answers 302 to its CDN with X-Linked-* [OBS owner-head-lfs]; the clone
        # redirects to its own resolve-cache instead (no xet Link header).
        location = f"{ctx.public_url}{cache_path}"
        return redirect(302, location, "Found", headers={
            "X-Repo-Commit": repo["sha"], "X-Linked-Size": str(meta.size), "X-Linked-Etag": f'"{meta.lfs_oid}"'})
    if repo["gated"] is False:
        # CFG-6 [OBS W s10-anon-resolve]: a non-gated repo redirects (relative Location) to resolve-cache,
        # with X-Repo-Commit [OBS 2026-10-06 W s10-anon-resolve].
        query = urlencode([(ctx.path, ""), ("etag", f'"{meta.oid}"')], quote_via=quote, safe="")
        return redirect(307, f"{cache_path}?{query}", "Temporary Redirect", headers={"X-Repo-Commit": repo["sha"]})
    return file_response(ctx, repo, path, lfs_object=False)  # [OBS owner-gitattributes, anon-readme]


def resolve_cache(ctx: Ctx, ns: str, name: str, sha: str, path: str) -> Response:
    """Target of the non-gated 307 (docs/system.md). Provisional: the same gate as resolve applies,
    so the redirect target cannot bypass gating; only the head commit sha resolves."""
    repo = visible_repo(ctx, f"{ns}/{name}", Fmt.PLAIN)
    gate(ctx, repo, Fmt.PLAIN, path)
    if sha != repo["sha"]:
        raise HttpError(error(404, REVISION_NOT_FOUND, Fmt.PLAIN, "RevisionNotFound"))
    meta = ctx.store.files[repo["id"]].files.get(path)
    if meta is None:
        raise HttpError(error(404, ENTRY_NOT_FOUND, Fmt.PLAIN, "EntryNotFound"))
    return file_response(ctx, repo, path, lfs_object=meta.is_lfs)


def raw(ctx: Ctx, ns: str, name: str, rev: str, path: str) -> Response:
    """ACC-10 [OBS raw-readme-*, anonymous-probes raw-readme]: the resolve gate and messages
    without the ACC-5 allowlist, then the file with resolve's headers. An LFS file is served as its
    pointer, and a non-gated repo serves the file directly, no 307 [OBS 2026-10-06 edge-cases e10, e12]."""
    repo = visible_repo(ctx, f"{ns}/{name}", Fmt.PLAIN)
    gate(ctx, repo, Fmt.PLAIN)  # path not passed: no allowlist
    check_revision(repo, rev, Fmt.PLAIN)
    if path not in ctx.store.files[repo["id"]].files:
        raise HttpError(error(404, ENTRY_NOT_FOUND, Fmt.PLAIN, "EntryNotFound"))
    return file_response(ctx, repo, path, git_blob=True)


BLOB_INLINE_MAX = 1 << 20


def blob(ctx: Ctx, ns: str, name: str, rev: str, path: str) -> Response:
    """The file page (HTML). [OBS anonymous-probes blob-config, 2026-10-06 blob]: an HTML page ignores
    the Bearer token (REQ-2), so the decision is the anonymous one, with the ACC-5 allowlist
    (README.md 200, other files and missing ones 401 GatedRepo, HTML, no WWW-Authenticate).
    Provisional (no Q yet): the page is a minimal one with the git blob content (the LFS pointer for
    LFS files), or only the size above 1 MiB; 404s are HTML like the other web routes."""
    repo = visible_repo(ctx, f"{ns}/{name}", Fmt.HTML)
    denied = domain.check_access(repo_id=repo["id"], gated=repo["gated"], owner=repo["author"], caller=None,
                                 request_status=None, path=path)
    if denied:
        raise HttpError(error(denied.status, denied.message, Fmt.HTML, "GatedRepo", www_authenticate=False))
    check_revision(repo, rev, Fmt.HTML)
    meta = ctx.store.files[repo["id"]].files.get(path)
    if meta is None:
        raise HttpError(error(404, ENTRY_NOT_FOUND, Fmt.HTML, "EntryNotFound"))
    if meta.is_lfs:
        shown = lfs_pointer(meta.lfs_oid, meta.size).decode()
    elif meta.size <= BLOB_INLINE_MAX:
        shown = b"".join(content_chunks(repo["id"], meta)).decode("utf-8", errors="replace")
    else:
        shown = f"{meta.size} bytes"
    page = (f'<!doctype html>\n<html><head><meta charset="utf-8"><title>{html.escape(path)} · '
            f'{html.escape(repo["id"])} at {html.escape(rev)}</title></head>\n'
            f"<body><h1>{html.escape(path)}</h1>\n<pre>{html.escape(shown)}</pre></body></html>\n")
    return respond(200, page.encode(), HTML_TYPE)


# --- owner side --------------------------------------------------------------------------------------

SETTINGS_ORDER = ("private", "visibility", "discussionsDisabled", "discussionsSorting", "gated",
                  "orgMembersGated", "gatedNotificationsEmail", "gatedNotificationsMode")
# CFG-3, CFG-7 [OBS]: `gated` is echoed, the notification fields are not. `private`/`visibility`
# echo like `gated` (client round-trip tests, CFG-4). Provisional: the others are not echoed.
ECHOED = ("private", "visibility", "gated")


def put_settings(ctx: Ctx, ns: str, name: str) -> Response:
    repo = owner_repo(ctx, f"{ns}/{name}", Fmt.API)
    body = api_body(ctx)

    def check(c: Checker) -> None:
        if not c.obj(body):
            return
        get = lambda k: body.get(k, MISSING)  # noqa: E731
        c.boolean(get("private"), "private")
        c.enum(get("visibility"), ("private", "public", "protected"), "visibility", optional=True)
        c.boolean(get("discussionsDisabled"), "discussionsDisabled")
        c.enum(get("discussionsSorting"), ("recently-created", "trending", "reactions"), "discussionsSorting",
               optional=True)
        gated = get("gated")
        if gated is not MISSING and not (gated is False or (isinstance(gated, str) and gated in ("auto", "manual"))):
            c.add("Invalid input", "gated")  # CFG-2: only false | "auto" | "manual"; Provisional wording
        c.boolean(get("orgMembersGated"), "orgMembersGated")
        email = get("gatedNotificationsEmail")
        if email is not MISSING:
            if not isinstance(email, str):
                c.string(email, "gatedNotificationsEmail")
            elif not EMAIL.match(email):
                c.add("Invalid email address", "gatedNotificationsEmail")  # Provisional wording
        c.enum(get("gatedNotificationsMode"), ("bulk", "real-time"), "gatedNotificationsMode", optional=True)

    validate(check)
    updates = {k: body[k] for k in SETTINGS_ORDER if k in body and k != "visibility"}
    if "visibility" in body:
        updates["private"] = body["visibility"] == "private"
    stamp = ctx.store.next_stamp()
    if any(repo.get(k, MISSING) != v for k, v in updates.items()):
        # CFG-6: changing the mode keeps every request where it is; only the config changes.
        repo.update(updates)
        ctx.store.commit_stamp(stamp)
    return json_ok({k: body[k] for k in SETTINGS_ORDER if k in body and k in ECHOED})


def list_requests(ctx: Ctx, ns: str, name: str, status: str) -> Response:
    """REV-10. The list answers even when the repo is not gated (CFG-6) [OBS W s10]."""
    repo = owner_repo(ctx, f"{ns}/{name}", Fmt.API)
    after, before, q = ctx.param("after"), ctx.param("before"), ctx.param("q")
    c = Checker()
    limit = c.int_query(ctx.param("limit"), "limit", minimum=10, maximum=1000)  # [OBS W s7-list-limit-5]
    for key, value in (("after", after), ("before", before)):
        if value is not None and not ISO_DATETIME.match(value):
            c.add("Invalid ISO datetime", key)  # Provisional wording
    if q is not None and len(q) > 250:
        c.add("Too big: expected string to have <=250 characters", "q")
    c.raise_if_any()
    limit = limit or 1000
    items = ctx.store.repo_requests(repo["id"], status)
    # Provisional (Q-10): after/before filter on `timestamp`, both exclusive.
    if after is not None:
        items = [r for r in items if parse_iso(r.timestamp) > parse_iso(after)]
    if before is not None:
        items = [r for r in items if parse_iso(r.timestamp) < parse_iso(before)]
    if q:
        # REV-10 [OBS 2026-10-06 edge-cases-a e0-search-*]: a case-insensitive prefix of the username
        # ("t", "TESTINGB" match TestingBOrig; "orig" and the fullname "bridge" do not).
        # Provisional (Q-21): e-mail matching is unobserved, so it is left out.
        needle = q.lower()
        items = [r for r in items if r.user.lower().startswith(needle)]
    headers = {}
    if len(items) > limit:
        # REV-10: `Link: <…>; rel="next"`. Provisional (Q-10): the next page is `after` = the last
        # timestamp of this page, other parameters kept.
        items = items[:limit]
        query = [(k, v) for k, v in ctx.query if k != "after"] + [("after", items[-1].timestamp)]
        url = f"{ctx.public_url}/api/models/{repo['id']}/user-access-request/{status}?{urlencode(query)}"
        headers["Link"] = f'<{url}>; rel="next"'
    return json_ok([list_item(ctx.store, r) for r in items], headers)


REASONS = ("rejectionReason", "resetReason")


def _check_handle_like(body: Any, *, with_status: bool) -> Callable[[Checker], None]:
    def check(c: Checker) -> None:
        if not c.obj(body):
            return
        check_user_ref(c, body)
        if with_status:
            c.enum(body.get("status", MISSING), domain.STATUSES, "status")
            for key in REASONS:
                c.string(body.get(key, MISSING), key, max_len=200)  # REV-2 [OBS W s7]
        if not c.issues:
            refine_user_ref(c, body)  # REV-5 [OBS W s7-handle-no-user]
    return check


def _target_user(ctx: Ctx, ref: dict) -> dict:
    user = find_user(ctx.store, ref)
    if user is None:
        raise HttpError(error(404, USER_NOT_FOUND, Fmt.API))  # [OBS W s7-handle-unknown-user]
    return user


def post_handle(ctx: Ctx, ns: str, name: str) -> Response:
    """§5.1. A reason sent with another status is accepted and ignored [OBS 2026-10-06 e7]. A non-gated
    repo → 400 RepoNotGated (REV-7). Provisional (Q-9): check order permission, not-gated, validation,
    unknown user, request lookup."""
    repo = owner_repo(ctx, f"{ns}/{name}", Fmt.API)
    if repo["gated"] is False:
        raise repo_not_gated(repo)
    body = api_body(ctx)
    validate(_check_handle_like(body, with_status=True))
    user = _target_user(ctx, body)["user"]
    stamp = ctx.store.next_stamp()
    try:
        change = domain.handle(ctx.store.get_request(repo["id"], user), body["status"],
                               now=format_iso(stamp), reviewer=ctx.username, reset_reason=body.get("resetReason"))
    except RequestNotFound:
        raise HttpError(error(404, REQUEST_NOT_FOUND, Fmt.API)) from None  # REV-1
    commit(ctx, repo, user, change, stamp)
    return json_ok({})  # [OBS C m1]


def post_grant(ctx: Ctx, ns: str, name: str) -> Response:
    """§5.2. A non-gated repo → 400 RepoNotGated (REV-7); the lists keep working (CFG-6).
    Provisional (Q-9): the same check order as handle; batch is unobserved and keeps no such check."""
    repo = owner_repo(ctx, f"{ns}/{name}", Fmt.API)
    if repo["gated"] is False:
        raise repo_not_gated(repo)
    body = api_body(ctx)
    validate(_check_handle_like(body, with_status=False))
    user = _target_user(ctx, body)["user"]
    stamp = ctx.store.next_stamp()
    try:
        change = domain.grant(ctx.store.get_request(repo["id"], user), repo=repo["id"], user=user,
                              owner=repo["author"], now=format_iso(stamp), reviewer=ctx.username)
    except AlreadyHasAccess:
        raise HttpError(error(400, ALREADY_HAS_ACCESS, Fmt.API)) from None  # REV-7 [OBS W s6]
    commit(ctx, repo, user, change, stamp)
    return json_ok({})  # [OBS W s6-grant-while-pending]


def post_batch(ctx: Ctx, ns: str, name: str) -> Response:
    """§5.3, REV-9: per-item outcomes in input order, echoing the identifier sent."""
    repo = owner_repo(ctx, f"{ns}/{name}", Fmt.API)
    body = api_body(ctx)

    def check(c: Checker) -> None:
        if not c.obj(body):
            return
        c.enum(body.get("status", MISSING), domain.STATUSES, "status")
        for key in REASONS:
            c.string(body.get(key, MISSING), key, max_len=200)
        requests = body.get("requests", MISSING)
        if c.array(requests, "requests", min_items=1, max_items=100):
            for i, item in enumerate(requests):
                if c.obj(item, "requests", i):
                    check_user_ref(c, item, "requests", i)
        if not c.issues:
            # Provisional (Q-9): each item needs exactly one of user / userId, like handle.
            for i, item in enumerate(requests):
                refine_user_ref(c, item, "requests", i)

    validate(check)
    stamp = ctx.store.next_stamp()
    now = format_iso(stamp)
    outcomes: list[dict] = []
    for item in body["requests"]:
        key = "user" if "user" in item else "userId"
        outcome: dict[str, Any] = {key: item[key]}
        target = find_user(ctx.store, item)
        if target is None:
            outcomes.append(outcome | {"ok": False, "error": "user_not_found"})  # [OBS W s8]
            continue
        try:
            change = domain.batch_item(ctx.store.get_request(repo["id"], target["user"]), body["status"],
                                       now=now, reviewer=ctx.username, reset_reason=body.get("resetReason"))
        except RequestNotFound:
            outcomes.append(outcome | {"ok": False, "error": "request_not_found"})
            continue
        commit(ctx, repo, target["user"], change, stamp)
        outcomes.append(outcome | {"ok": True})
    return json_ok(outcomes)


def post_cancel(ctx: Ctx, ns: str, name: str) -> Response:
    """Requester self-cancel (REQ-7 [OBS 2026-10-06]): a pending request is deleted, `200 {"ok":true}`;
    otherwise 404 "No pending access request…" and no change."""
    if ctx.caller is None:
        raise HttpError(error(401, INVALID_CREDENTIALS, Fmt.API))
    repo = visible_repo(ctx, f"{ns}/{name}", Fmt.API)
    stamp = ctx.store.next_stamp()
    try:
        change = domain.cancel(ctx.store.get_request(repo["id"], ctx.username))
    except RequestNotFound:
        raise HttpError(error(404, NO_PENDING_REQUEST, Fmt.API)) from None
    commit(ctx, repo, ctx.username, change, stamp)
    return json_ok({"ok": True})


def report(ctx: Ctx, ns: str, name: str) -> Response:
    """REP-1: every request in every status. [OBS owner-reads, W s11] for a pending entry, [OBS
    2026-10-06 W s1] for an accepted one (reviewedAt before status, then grantedBy)."""
    repo = owner_repo(ctx, f"{ns}/{name}", Fmt.HTML)
    entries = []
    for req in ctx.store.repo_requests(repo["id"]):  # Provisional (Q-14): list order, all statuses
        u = ctx.store.users[req.user]
        entry: dict[str, Any] = {"fullname": u["fullname"], "user": u["user"]}
        if req.emailShared:
            entry["email"] = u["email"]  # Provisional (Q-14): no email for granted users, as in lists
        entry["time"] = req.timestamp
        if req.reviewedAt is not None:
            entry["reviewedAt"] = req.reviewedAt  # REP-1 [OBS 2026-10-06 W s1]
        entry["status"] = req.status
        if req.grantedBy is not None:
            g = ctx.store.users[req.grantedBy]
            entry["grantedBy"] = {"fullname": g["fullname"], "user": g["user"]}  # REP-1 [OBS 2026-10-06 W s1]
        entries.append(entry)
    disposition = f"attachment; filename=user-access-report-{ns}-{name}.json"
    # No ETag on the report [OBS 2026-10-06 owner-reads, W s1/s11: ETag kept for other responses].
    return respond(200, dumps(entries), "application/json", {"Content-Disposition": disposition}, etag=False)


# --- requester side ---------------------------------------------------------------------------------


def _form_answers(ctx: Ctx) -> Any:
    """REQ-2: JSON or form-encoded body (same result [OBS]). Provisional: other bodies are an
    error (zod's record check), an empty body is `{}`."""
    if not ctx.body.strip():
        return {}
    media = (ctx.content_type or "").split(";")[0].strip().lower()
    if media == "application/x-www-form-urlencoded":
        answers: dict[str, str] = {}
        for k, v in parse_qsl(ctx.body.decode("utf-8", errors="replace"), keep_blank_values=True):
            answers.setdefault(k, v)
        return answers
    try:
        return json.loads(ctx.body)
    except ValueError:
        return MISSING


def _stored_value(value: Any) -> str:
    # Answers are strings [SPEC]. Provisional (Q-15): other JSON values are stored as JSON text.
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def ask_access(ctx: Ctx, ns: str, name: str) -> Response:
    repo_id = f"{ns}/{name}"
    if ctx.caller is None:
        raise HttpError(error(401, INVALID_CREDENTIALS, Fmt.HTML))  # Provisional (Q-1, REQ-1)
    repo = visible_repo(ctx, repo_id, Fmt.HTML)
    answers = _form_answers(ctx)
    validate(lambda c: c.obj(answers, kind="record"))
    labels = (repo.get("cardData") or {}).get("extra_gated_fields")
    # Stored answers: the card's field labels present in the body, in card order (gate-form.md §2).
    # Provisional (Q-16): no required-field validation; unknown keys are dropped.
    fields = {label: _stored_value(answers[label]) for label in labels if label in answers} if labels else None
    stamp = ctx.store.next_stamp()
    change = domain.ask_access(ctx.store.get_request(repo["id"], ctx.username), repo=repo["id"],
                               user=ctx.username, gated=repo["gated"], now=format_iso(stamp), fields=fields)
    commit(ctx, repo, ctx.username, change, stamp)
    # REQ-2 [OBS]: 303 to the repo page. Location is the backend's own URL (system.md URL
    # rewriting); the body keeps huggingface.co, exactly as recorded through the bridge.
    return redirect(303, f"{ctx.public_url}/{repo_id}", "See Other", body_target=f"https://huggingface.co/{repo_id}")


# --- routing -----------------------------------------------------------------------------------------

_NAME = r"[A-Za-z0-9_.-]+"
_REPO = rf"(?P<ns>{_NAME})/(?P<name>{_NAME})"
_WEB_REPO = rf"(?!api/){_REPO}"  # web routes: the `api` namespace is reserved

Handler = Callable[..., Response]
ROUTES: list[tuple[frozenset[str], re.Pattern[str], Fmt, Handler]] = [
    (frozenset(m.split()), re.compile(p), f, h)
    for m, p, f, h in [
        ("GET", r"/api/whoami-v2", Fmt.API, whoami),
        ("GET", r"/api/quicksearch", Fmt.API, quicksearch),
        ("GET", rf"/api/models/{_REPO}", Fmt.API, model_info),
        ("GET", rf"/api/models/{_REPO}/tree/(?P<rev>[^/]+)(?:/(?P<path>.*))?", Fmt.API, tree),
        ("GET", rf"/api/models/{_REPO}/auth-check", Fmt.API, auth_check),
        ("PUT", rf"/api/models/{_REPO}/settings", Fmt.API, put_settings),
        ("GET", rf"/api/models/{_REPO}/user-access-request/(?P<status>pending|accepted|rejected|reset)",
         Fmt.API, list_requests),
        ("POST", rf"/api/models/{_REPO}/user-access-request/handle", Fmt.API, post_handle),
        ("POST", rf"/api/models/{_REPO}/user-access-request/grant", Fmt.API, post_grant),
        ("POST", rf"/api/models/{_REPO}/user-access-request/batch", Fmt.API, post_batch),
        ("POST", rf"/api/models/{_REPO}/user-access-request/cancel", Fmt.API, post_cancel),
        ("POST", rf"/{_WEB_REPO}/ask-access", Fmt.HTML, ask_access),
        ("GET", rf"/{_WEB_REPO}/user-access-report", Fmt.HTML, report),
        ("GET HEAD", rf"/{_WEB_REPO}/resolve/(?P<rev>[^/]+)/(?P<path>.+)", Fmt.PLAIN, resolve),
        ("GET HEAD", rf"/{_WEB_REPO}/raw/(?P<rev>[^/]+)/(?P<path>.+)", Fmt.PLAIN, raw),  # HEAD [OBS 2026-10-06]
        ("GET HEAD", rf"/{_WEB_REPO}/blob/(?P<rev>[^/]+)/(?P<path>.+)", Fmt.HTML, blob),
        ("GET HEAD", rf"/api/resolve-cache/models/{_REPO}/(?P<sha>[^/]+)/(?P<path>.+)", Fmt.PLAIN, resolve_cache),
    ]
]


def dispatch(ctx: Ctx) -> Response:
    """Route a decoded path. Anything outside the surface is HF's 404 page [OBS owner-get-settings,
    anon-ask-access-get]: JSON under /api, HTML elsewhere, no X-Error-Code."""
    not_found = error(404, PAGE_NOT_FOUND, Fmt.API if ctx.path.startswith("/api/") else Fmt.HTML)
    if any(seg in (".", "..") for seg in ctx.path.split("/")):
        return not_found
    for methods, pattern, fmt, handler in ROUTES:
        match = pattern.fullmatch(ctx.path)
        if match is None or ctx.method not in methods:
            continue
        try:
            if ctx.invalid_token:
                # docs/system.md "Personas": any unknown bearer → 401 [OBS whoami-bad-token]
                return error(401, INVALID_CREDENTIALS, fmt)
            return handler(ctx, **match.groupdict())
        except HttpError as exc:
            return exc.response
        except ValidationFailed as exc:
            # REV-12: 400, zod pretty body, sanitised header, no X-Error-Code [OBS W s7]
            return error(400, exc.pretty(), fmt)
    return not_found
