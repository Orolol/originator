"""The bridge app: allowlisted pass-through to the real Hub, with persona tokens and an exchange log."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from http.cookiejar import DefaultCookiePolicy
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse

from .config import Settings
from .exchange_log import ExchangeLog, summarize_request_body, summarize_response_body, utc_now_iso
from .proxy import (
    INVALID_CREDENTIALS,
    WWW_AUTHENTICATE,
    REQUEST_HEADERS,
    RESPONSE_HEADERS,
    USER_AGENT,
    filter_response_headers,
    identify_persona,
)
from .routes import match_route

TIMEOUT = httpx.Timeout(30.0)
# The catch-all must see every method so that unknown ones get 404 BridgeRouteNotAllowed, not 405.
ALL_METHODS = ["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "TRACE"]


def error_response(status: int, message: str, code: str | None = None) -> Response:
    headers = {"X-Error-Message": message}
    if code:
        headers["X-Error-Code"] = code
    if status == 401:
        headers["WWW-Authenticate"] = WWW_AUTHENTICATE
    return JSONResponse({"error": message}, status_code=status, headers=headers)


def create_app(settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    """`transport` replaces the network (tests pass an `httpx.MockTransport`)."""
    log = ExchangeLog(settings.log_file, secrets=settings.tokens.values())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # No redirects, no retries: one upstream call per incoming call (docs/system.md).
        async with httpx.AsyncClient(
            transport=transport,
            follow_redirects=False,
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            # Never keep upstream cookies: a session cookie from one persona must not reach another.
            client.cookies.jar.set_policy(DefaultCookiePolicy(allowed_domains=[]))
            app.state.client = client
            yield

    app = FastAPI(title="bridge", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/__bridge__/health")
    async def health():
        return {
            "ok": True,
            "upstream": settings.upstream,
            "public_url": settings.public_url,
            "repos": list(settings.repos),
            "personas": {name: name in settings.tokens for name in ("owner", "requester")},
        }

    @app.get("/__bridge__/log")
    async def get_log(limit: int = Query(100, ge=1)):
        return log.entries(limit)

    @app.delete("/__bridge__/log")
    async def clear_log():
        return {"cleared": log.clear()}

    @app.api_route("/{path:path}", methods=ALL_METHODS, include_in_schema=False)
    async def proxy(request: Request) -> Response:
        started_at = utc_now_iso()
        t0 = time.perf_counter()
        path = request.scope["path"]  # decoded (request.url.path would cut at a decoded "?" or "#")
        raw_path = request.scope.get("raw_path") or quote(path).encode("ascii")
        raw_query = request.scope["query_string"]
        body = await request.body()
        persona = identify_persona(request.headers.get("authorization"))

        response, upstream_called = await handle(request, path, persona, raw_path, raw_query, body)

        log.record(
            started_at=started_at,
            duration_ms=round((time.perf_counter() - t0) * 1000, 1),
            persona=persona or "invalid",
            method=request.method,
            path=raw_path.decode("latin-1"),
            query=raw_query.decode("latin-1"),
            upstream=upstream_called,
            request_body=summarize_request_body(request.headers.get("content-type"), body),
            status=response.status_code,
            response_headers={n: response.headers[n] for n in RESPONSE_HEADERS if n in response.headers},
            response_body=summarize_response_body(response.headers.get("content-type"), response.body),
        )
        return response

    async def handle(
        request: Request, path: str, persona: str | None, raw_path: bytes, raw_query: bytes, body: bytes
    ) -> tuple[Response, bool]:
        """Returns the response and whether the upstream was called."""
        # Match on the decoded path; forward the raw one so encodings (e.g. %2F in a revision) survive.
        matched = match_route(request.method, path)
        if matched is None:
            return error_response(
                404,
                f"Route not allowed by bridge: {request.method} {raw_path.decode('latin-1')}",
                "BridgeRouteNotAllowed",
            ), False
        if matched.repo is not None and matched.repo not in settings.repos:
            return error_response(403, f"Repo not allowed by bridge: {matched.repo}", "BridgeRepoNotAllowed"), False
        if persona is None:
            return error_response(401, INVALID_CREDENTIALS), False

        headers = {n: request.headers[n] for n in REQUEST_HEADERS if n in request.headers}
        if persona != "anonymous":
            token = settings.tokens.get(persona)
            if token is None:  # fail loudly instead of silently downgrading to anonymous
                return error_response(
                    503, f"Persona token not configured in bridge: {persona}", "BridgePersonaNotConfigured"
                ), False
            headers["Authorization"] = f"Bearer {token}"

        url = httpx.URL(settings.upstream).copy_with(raw_path=raw_path + (b"?" + raw_query if raw_query else b""))
        client: httpx.AsyncClient = app.state.client
        try:
            upstream = await client.send(
                client.build_request(request.method, url, headers=headers, content=body or None)
            )
        except httpx.TimeoutException:
            return error_response(504, "Upstream timed out", "BridgeUpstreamTimeout"), True
        except httpx.HTTPError as exc:
            # Only the exception class: its text can embed the request URL.
            return error_response(502, f"Upstream request failed: {type(exc).__name__}", "BridgeUpstreamError"), True

        kept = filter_response_headers(upstream.headers.raw, settings.upstream, settings.public_url)
        return Response(content=upstream.content, status_code=upstream.status_code, headers=kept), True

    return app
