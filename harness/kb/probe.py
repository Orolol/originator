#!/usr/bin/env python3
"""Run a list of HTTP probes against a live target and record what it answers.

Target-agnostic: the cases live in a JSON file (see harness/kb/probes/*.json) and run in order.
Each case is:

    {"id", "method", "url", "note"?,
     "auth"?: "ENV_VAR_NAME",            # send `Authorization: Bearer $ENV_VAR_NAME` (value from --env-file)
     "body"?: {...}, "body_encoding"?: "json" | "form",
     "wait"?: seconds,                   # sleep before the request (eventual consistency)
     "keep_text"?: true,                 # store the full body when ≤ 20 kB (small files used as seeds)
     "extract_props"?: "Component",      # capture JSON `data-props` of a server-rendered `data-target`
     "extract_text"?: {"from": regex, "lines": n}}   # n visible text nodes from the first match

Redirects are NOT followed, so a 302/303 is recorded as-is. Long strings are truncated, so we never
store whole licence texts. Every secret value from --env-file is replaced by `<ENV_VAR_NAME>` and
every e-mail address by `<email>` before anything is written.

Read-only by default: any method other than GET/HEAD needs --allow-writes. Use writes only on
sandbox repos owned by our own accounts, and only when the user asked for that action.

Output: a JSON record (machine-readable fixture) and a Markdown table (for the KB).

    python3 harness/kb/probe.py harness/kb/probes/hf-gated-anonymous.json \
        --out-json docs/hf-gated/observations/2026-10-05-anonymous-probes.json \
        --out-md docs/hf-gated/observations/2026-10-05-anonymous-probes.md
"""

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KEPT_HEADERS = (
    "x-error-code", "x-error-message", "content-type", "content-disposition", "location", "link", "www-authenticate",
    "etag", "x-repo-commit", "x-linked-size", "x-linked-etag", "content-length",
)
MAX_STRING = 200
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def load_env(path):
    values = {}
    if path:
        with open(path) as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def truncate(node):
    if isinstance(node, dict):
        return {k: truncate(v) for k, v in node.items()}
    if isinstance(node, list):
        return [truncate(v) for v in node]
    if isinstance(node, str) and len(node) > MAX_STRING:
        return node[:MAX_STRING] + f"…[+{len(node) - MAX_STRING} chars]"
    return node


def redact(node, secrets):
    if isinstance(node, dict):
        return {k: redact(v, secrets) for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v, secrets) for v in node]
    if isinstance(node, str):
        for name, value in secrets.items():
            if value:
                node = node.replace(value, f"<{name}>")
        return EMAIL.sub("<email>", node)
    return node


def run_case(opener, case, env, allow_writes):
    method = case.get("method", "GET")
    if method not in ("GET", "HEAD") and not allow_writes:
        raise ValueError(f"{case['id']}: {method} changes state; pass --allow-writes if that is intended")
    if case.get("wait"):
        time.sleep(case["wait"])
    headers = {"User-Agent": "originator-kb-probe/1"}
    if case.get("auth"):
        headers["Authorization"] = f"Bearer {env[case['auth']]}"
    data = None
    if "body" in case:
        if case.get("body_encoding", "json") == "form":
            data = urllib.parse.urlencode(case["body"]).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(case["body"]).encode()
            headers["Content-Type"] = "application/json"
    request = urllib.request.Request(case["url"], data=data, method=method, headers=headers)
    sent_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    try:
        response = opener.open(request, timeout=30)
        status, response_headers, body = response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        status, response_headers, body = error.code, error.headers, error.read()
    text = body.decode("utf-8", errors="replace")
    kept_headers = {k: response_headers[k] for k in KEPT_HEADERS if response_headers.get(k) is not None}
    location = kept_headers.get("location")
    if location and urllib.parse.urlsplit(location).netloc not in ("", urllib.parse.urlsplit(case["url"]).netloc):
        # Cross-host redirects (CDN) carry signed, expiring query strings: never store them.
        kept_headers["location"] = urllib.parse.urlsplit(location)._replace(query="<signed-query-redacted>").geturl()
    record = {
        "id": case["id"],
        "as": case.get("auth") or "anonymous",
        "method": method,
        "url": case["url"],
        "request_body": case.get("body"),
        "request_encoding": case.get("body_encoding", "json") if "body" in case else None,
        "note": case.get("note"),
        "sent_at": sent_at,  # lets server-side timestamps be matched to the request that set them
        "status": status,
        "headers": kept_headers,
        "body_excerpt": None if text.lstrip().lower().startswith("<!doctype") else text[:160],
    }
    if case.get("keep_text") and len(text) <= 20_000:
        record["body_text"] = text  # full small text file (seed fixtures for the clone)
    if "json" in (response_headers.get("content-type") or "") and len(text) <= 2_000_000:
        try:
            record["body_json"] = json.loads(text)  # full structure (list items, reviewedAt, grantedBy…)
        except ValueError:
            pass
    if case.get("extract_props"):
        pattern = r'data-target="%s"[^>]*?data-props="([^"]*)"' % re.escape(case["extract_props"])
        match = re.search(pattern, text)
        record["props"] = truncate(json.loads(html.unescape(match.group(1)))) if match else None
    if case.get("extract_text"):
        # Visible text lines (tags and scripts stripped), from the first line matching `from`, `lines` long.
        visible = re.sub(r"<(script|style)\b.*?</\1>", "", text, flags=re.S)
        visible = re.sub(r'\sdata-props="[^"]*"', "", visible)  # JSON props may contain raw '>'
        visible = re.sub(r"<[^>]+>", "\n", visible)
        lines = [html.unescape(line.strip()) for line in visible.split("\n") if line.strip()]
        anchor = re.compile(case["extract_text"]["from"])
        start = next((i for i, line in enumerate(lines) if anchor.search(line)), None)
        count = case["extract_text"].get("lines", 10)
        record["visible_text"] = None if start is None else [truncate(line) for line in lines[start : start + count]]
    return record


def to_markdown(meta, records):
    lines = [
        f"# Probe results: {meta['cases_file']}",
        "",
        f"Recorded {meta['recorded_at']} by `harness/kb/probe.py` (no cookies, redirects not followed; "
        "`as` = identity used, secrets and e-mails redacted).",
        "Regenerate with the command in the script docstring. Do not hand-edit: re-run instead.",
        "",
        "| id | as | request | status | X-Error-Code | X-Error-Message / Location / body excerpt | note |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in records:
        message = (
            r["headers"].get("x-error-message")
            or (r["headers"].get("location") and f"Location: {r['headers']['location']}")
            or (r["body_excerpt"] or "").replace("\n", " ")[:90]
        )
        message = message.replace("|", "\\|")
        request = f"{r['method']} {r['url'].replace('https://huggingface.co', '')}"
        if r.get("request_body") is not None:
            request += f" ({r['request_encoding']} {json.dumps(r['request_body'], ensure_ascii=False)})"
        lines.append(
            f"| {r['id']} | {r['as']} | `{request}` | {r['status']} "
            f"| {r['headers'].get('x-error-code', '')} | {message} | {r['note'] or ''} |"
        )
    props = [r for r in records if r.get("props") is not None]
    if props:
        lines += ["", "## Extracted component props", ""]
        for r in props:
            lines += [f"### {r['id']}", "", "```json", json.dumps(r["props"], indent=1, ensure_ascii=False), "```", ""]
    texts = [r for r in records if r.get("visible_text") is not None]
    if texts:
        lines += ["", "## Extracted visible text (one line per text node)", ""]
        for r in texts:
            lines += [f"### {r['id']}", ""] + [f"{i + 1}. {line}" for i, line in enumerate(r["visible_text"])] + [""]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--env-file", default=None, help="KEY=VALUE file providing the tokens named by `auth`")
    parser.add_argument("--allow-writes", action="store_true", help="allow non-GET/HEAD cases (state changes)")
    args = parser.parse_args()

    with open(args.cases) as handle:
        cases = json.load(handle)
    env = load_env(args.env_file)
    missing = sorted({c["auth"] for c in cases if c.get("auth")} - env.keys())
    if missing:
        parser.error(f"missing from --env-file: {', '.join(missing)}")
    opener = urllib.request.build_opener(NoRedirect)
    records = []
    for case in cases:
        records.append(run_case(opener, case, env, args.allow_writes))
        print(f"{case['id']}: {records[-1]['status']}", file=sys.stderr)
    records = redact(records, env)
    meta = {
        "cases_file": args.cases,
        "recorded_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(args.out_json, "w") as handle:
        json.dump({"_meta": meta, "records": records}, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    with open(args.out_md, "w") as handle:
        handle.write(to_markdown(meta, records))
    print(f"{len(records)} probes -> {args.out_json}, {args.out_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
