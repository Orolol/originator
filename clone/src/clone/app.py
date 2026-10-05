"""The clone app: HF's wire protocol (protocol.py) plus the `/__clone__/` control endpoints
(docs/system.md "Clone: contract"). One in-memory Store per app; handlers never await between
reading and writing state, so requests apply atomically and in arrival order.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response, StreamingResponse

from .exchange_log import RESPONSE_HEADERS, clean, summarize_request_body, summarize_response_body
from .protocol import Ctx, dispatch, identify
from .store import DEFAULT_SEED, SeedError, Store, builtin_seed, builtin_seed_names, parse_iso

DEFAULT_PUBLIC_URL = "http://127.0.0.1:8200"
# The catch-all sees every method, so unknown ones get HF's 404 rather than a framework 405.
ALL_METHODS = ["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]


def _bad_request(message: str, **extra: Any) -> JSONResponse:
    return JSONResponse({"error": message, **extra}, status_code=400)


async def _json_body(request: Request) -> Any:
    raw = await request.body()
    return json.loads(raw) if raw.strip() else None


def _head(response: Response) -> Response:
    """HEAD: the GET headers (Content-Length included), no body [OBS owner-head-gitattributes]."""
    return Response(content=b"", status_code=response.status_code, headers=dict(response.headers))


def create_app(store: Store | None = None, public_url: str = DEFAULT_PUBLIC_URL) -> FastAPI:
    store = store if store is not None else Store()
    public_url = public_url.rstrip("/")
    app = FastAPI(title="clone", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store

    def health() -> dict:
        return {"ok": True, "seed": store.seed_name, "now": store.now}

    def clock() -> dict:
        return {"now": store.now, "tick_ms": store.tick_ms}

    @app.get("/__clone__/health")
    async def get_health():
        return health()

    @app.post("/__clone__/reset")
    async def reset(request: Request):
        try:
            body = await _json_body(request)
        except ValueError:
            return _bad_request("body must be JSON")
        name = DEFAULT_SEED if body is None else body.get("seed", DEFAULT_SEED) if isinstance(body, dict) else None
        if not isinstance(name, str):
            return _bad_request('body must be {"seed": "<built-in seed name>"}')
        try:
            store.load(builtin_seed(name))
        except SeedError as exc:
            return JSONResponse({"error": str(exc), "seeds": builtin_seed_names()}, status_code=404)
        return health()

    @app.get("/__clone__/state")
    async def get_state():
        return store.dump()

    @app.put("/__clone__/state")
    async def put_state(request: Request):
        try:
            store.load(await _json_body(request))
        except ValueError as exc:  # SeedError included
            return _bad_request(f"invalid seed document: {exc}")
        return health()

    @app.get("/__clone__/clock")
    async def get_clock():
        return clock()

    @app.post("/__clone__/clock")
    async def set_clock(request: Request):
        try:
            body = await _json_body(request)
        except ValueError:
            return _bad_request("body must be JSON")
        if not isinstance(body, dict) or len(body.keys() & {"now", "advance_ms"}) != 1:
            return _bad_request('body must be {"now": "<iso>"} or {"advance_ms": <n >= 0>}')
        if "now" in body:
            try:
                store.now_ms = parse_iso(body["now"])
            except (TypeError, ValueError):
                return _bad_request("now must be an ISO 8601 date-time")
        else:
            step = body["advance_ms"]
            if not isinstance(step, int) or isinstance(step, bool) or step < 0:
                return _bad_request("advance_ms must be a non-negative integer")
            store.now_ms += step
        return clock()

    @app.get("/__clone__/outbox")
    async def get_outbox():
        return store.outbox

    @app.delete("/__clone__/outbox")
    async def clear_outbox():
        count = len(store.outbox)
        store.outbox.clear()
        return {"cleared": count}

    @app.get("/__clone__/log")
    async def get_log(limit: int = Query(100, ge=1)):
        return list(store.log)[-limit:]  # newest last, like /__bridge__/log

    @app.delete("/__clone__/log")
    async def clear_log():
        count = len(store.log)
        store.log.clear()
        return {"cleared": count}

    @app.api_route("/__clone__/{rest:path}", methods=ALL_METHODS, include_in_schema=False)
    async def unknown_control(rest: str):
        return JSONResponse({"error": f"Unknown control endpoint: /__clone__/{rest}"}, status_code=404)

    @app.api_route("/{path:path}", methods=ALL_METHODS, include_in_schema=False)
    async def hub(request: Request) -> Response:
        body = await request.body()
        started_at = store.now  # the virtual clock, before any tick this request causes
        persona, caller = identify(store, request.headers.get("authorization"))
        ctx = Ctx(
            store=store, public_url=public_url, method=request.method, path=request.scope["path"],
            caller=caller, invalid_token=persona == "invalid",
            query=[(k, v) for k, v in request.query_params.multi_items()],
            body=body, content_type=request.headers.get("content-type"),
        )
        response = dispatch(ctx)
        if request.method == "HEAD":
            response = _head(response)
        if isinstance(response, StreamingResponse):
            logged_body: Any = {"bytes": int(response.headers.get("content-length", 0))}
        else:
            logged_body = summarize_response_body(response.headers.get("content-type"), response.body)
        raw_path = request.scope.get("raw_path") or request.scope["path"].encode()
        store.record(**clean({
            "started_at": started_at,
            "duration_ms": 0,
            "persona": persona,
            "method": request.method,
            "path": raw_path.decode("latin-1"),
            "query": request.scope["query_string"].decode("latin-1"),
            "upstream": False,
            "request_body": summarize_request_body(request.headers.get("content-type"), body),
            "status": response.status_code,
            "response_headers": {n: response.headers[n] for n in RESPONSE_HEADERS if n in response.headers},
            "response_body": logged_body,
        }))
        return response

    return app
