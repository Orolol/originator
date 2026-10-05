"""Route allowlist: the only (method, path) pairs the bridge forwards (docs/system.md "Backend surface")."""

from __future__ import annotations

import re
from dataclasses import dataclass

_NAME = r"[A-Za-z0-9_.-]+"
# `{repo}` = `ns/name`. Web routes (no /api prefix) exclude the reserved `api` namespace so that
# e.g. `/api/models/ask-access` cannot be read as a repo called `api/models`.
_API_REPO = rf"(?P<repo>{_NAME}/{_NAME})"
_WEB_REPO = rf"(?P<repo>(?!api/){_NAME}/{_NAME})"


@dataclass(frozen=True)
class Route:
    methods: frozenset[str]
    pattern: re.Pattern[str]


def _route(methods: str, pattern: str) -> Route:
    return Route(frozenset(methods.split()), re.compile(pattern))


ROUTES = [
    _route("GET", r"/api/whoami-v2"),
    _route("GET", r"/api/quicksearch"),
    _route("GET", rf"/api/models/{_API_REPO}"),
    _route("GET", rf"/api/models/{_API_REPO}/tree/[^/]+(/.+)?"),
    _route("GET", rf"/api/models/{_API_REPO}/auth-check"),
    _route("PUT", rf"/api/models/{_API_REPO}/settings"),
    _route("GET", rf"/api/models/{_API_REPO}/user-access-request/(pending|accepted|rejected|reset)"),
    _route("POST", rf"/api/models/{_API_REPO}/user-access-request/(handle|grant|batch|cancel)"),
    _route("POST", rf"/{_WEB_REPO}/ask-access"),
    _route("GET", rf"/{_WEB_REPO}/user-access-report"),
    _route("GET HEAD", rf"/{_WEB_REPO}/resolve/[^/]+/.+"),
    _route("GET", rf"/{_WEB_REPO}/raw/[^/]+/.+"),  # ACC-10
    _route("GET", rf"/{_WEB_REPO}/blob/[^/]+/.+"),  # ACC-5 (HTML page)
]


@dataclass(frozen=True)
class Match:
    repo: str | None  # None for routes that are not repo-scoped (whoami-v2, quicksearch)


def match_route(method: str, path: str) -> Match | None:
    """Match a *decoded* request path; None means the route is not allowed."""
    # httpx collapses dot segments, so `…/resolve/main/../../Other/repo/…` would leave the
    # allowlisted repo upstream. Refuse such paths outright.
    if any(segment in (".", "..") for segment in path.split("/")):
        return None
    for route in ROUTES:
        if method in route.methods and (m := route.pattern.fullmatch(path)):
            return Match(repo=m.groupdict().get("repo"))
    return None
