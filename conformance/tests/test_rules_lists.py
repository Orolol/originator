"""Owner lists: pagination, search, query validation (REV-10, REV-11, Q-21)."""

from __future__ import annotations

import pytest

from conformance import expect as E
from conformance.compare import Context, TimestampTracker, _norm_origin_url
from conformance.config import RECORDED_ORIGINS
from conformance.rule_seeds import CAROL, MANUAL, REQUESTER, pending, rules_seed

COUNT = 25


def paged_seed():
    requests = [pending(f"conf-user-{i:02d}", f"2026-10-05T10:{i:02d}:00.000Z") for i in range(1, COUNT + 1)]
    return rules_seed(requests, users=COUNT)


def follow(be, first_query: str) -> list[list[dict]]:
    pages = []
    response = be.list_requests(MANUAL, "pending", first_query)
    while True:
        E.assert_ok(response)
        pages.append(response.json())
        link = response.links.get("next")
        if not link:
            return pages
        url = link["url"]
        ctx = Context(TimestampTracker(set()), be.base_url, RECORDED_ORIGINS)
        assert _norm_origin_url(url, ctx).startswith(f"<origin>/api/models/{MANUAL}/user-access-request/pending?"), url
        assert url.startswith(be.base_url), f"next page must stay on the backend (system.md URL rewriting): {url}"
        response = be.req("owner", "GET", url[len(be.base_url):])
        assert len(pages) < 10, "pagination does not terminate"


def test_REV_10_pagination_with_link_next(be):
    be.put_state(paged_seed())
    pages = follow(be, "?limit=10")
    assert [len(page) for page in pages] == [10, 10, 5]
    users = [item["user"]["user"] for page in pages for item in page]
    assert len(users) == len(set(users)) == COUNT
    assert set(users) == {f"conf-user-{i:02d}" for i in range(1, COUNT + 1)}


def test_REV_10_default_limit_is_one_page_without_link(be):
    be.put_state(paged_seed())
    response = be.list_requests(MANUAL, "pending")
    E.assert_ok(response)
    assert len(response.json()) == COUNT
    assert "link" not in response.headers  # [OBS] a single page has no Link header


@pytest.mark.parametrize("query,expected", [
    ("?limit=5", ("Too small: expected number to be >=10", "limit")),  # [OBS] s7-list-limit-5
    ("?limit=9", ("Too small: expected number to be >=10", "limit")),
    ("?limit=1001", None),  # SPEC: 10-1000
    ("?q=" + "a" * 251, None),  # SPEC: q at most 250 characters
])
def test_REV_10_query_validation(be, query, expected):
    be.put_state(rules_seed())
    response = be.list_requests(MANUAL, "accepted", query)
    if expected:
        E.assert_error(response, 400, E.zod(*expected), body="zod")
    else:
        assert response.status_code == 400, E.describe(response)
        assert "x-error-code" not in response.headers
        assert response.headers["x-error-message"] == E.ascii_header(response.json()["error"])


def test_REV_10_limit_bounds_accepted(be):
    be.put_state(paged_seed())
    for limit in (10, 1000):
        response = be.list_requests(MANUAL, "pending", f"?limit={limit}")
        E.assert_ok(response)
        assert len(response.json()) == min(limit, COUNT)


@pytest.mark.parametrize("q,expected", [
    ("testingb", {REQUESTER}),  # [OBS] s7-list-q: lower-case prefix of the username
    ("TESTINGB", {REQUESTER}),  # case-insensitive [OBS Q-21 partial]
    ("TestingBOrig", {REQUESTER}),
    # [OBS 2026-10-06 search, edge-cases-a e0-search-*]: the fullname "Bridge" is NOT searched (any case), and
    # a username substring does not match; this overrides the SPEC's "username, fullname, email…".
    ("Bridge", set()),
    ("bridge", set()),
    ("estingB", set()),
    ("t", {REQUESTER}),
    ("DemoC", {CAROL}),
    ("zzz-no-match", set()),
])
def test_REV_10_search_q(be, q, expected):
    be.put_state(rules_seed([pending(REQUESTER, "2026-10-05T14:00:00.000Z"), pending(CAROL, "2026-10-05T14:01:00.000Z")]))
    response = be.list_requests(MANUAL, "pending", f"?q={q}")
    E.assert_ok(response)
    assert {item["user"]["user"] for item in response.json()} == expected


def test_REV_11_reset_list_exists_server_side(be):
    # REV-11: the Python client lacks it, the server has it ([OBS] s5-list-reset)
    be.put_state(rules_seed())
    response = be.list_requests(MANUAL, "reset")
    E.assert_ok(response)
    assert response.json() == []

