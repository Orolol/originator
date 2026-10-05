#!/usr/bin/env python3
"""Export the bridge exchange log as a redacted fixture: "which requests did this session fire?".

Fetches `GET /__bridge__/log` from a running bridge and writes JSON + a Markdown table. E-mail
addresses are redacted (the bridge already never logs tokens). Use it right after a scripted or
manual UI walkthrough; clear the log (`DELETE /__bridge__/log`) before starting the walkthrough.

    python3 harness/kb/bridge_log_to_md.py --title "UI walkthrough" \
        --out-json docs/hf-gated/observations/2026-10-05-ui-walkthrough.json \
        --out-md docs/hf-gated/observations/2026-10-05-ui-walkthrough.md

`--log-url` exports any other log endpoint in the same schema, for example the clone's
(`GET /__clone__/log`, cleared with `DELETE /__clone__/log`):

    python3 harness/kb/bridge_log_to_md.py --log-url http://127.0.0.1:8201/__clone__/log \
        --title "Clone walkthrough" --out-json out.json --out-md out.md
"""

import argparse
import json
import re
import sys
import urllib.request

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact(node):
    if isinstance(node, dict):
        return {k: redact(v) for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v) for v in node]
    if isinstance(node, str):
        return EMAIL.sub("<email>", node)
    return node


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bridge", default="http://127.0.0.1:8100")
    parser.add_argument(
        "--log-url",
        help="full URL of a log endpoint in the bridge-log schema (for example the clone's "
        "http://127.0.0.1:8201/__clone__/log); overrides --bridge. `limit=10000` is added when the URL has no "
        "`limit` parameter (the clone's default is 100)",
    )
    parser.add_argument("--title", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()

    if args.log_url:
        log_url = args.log_url
        if "limit=" not in log_url:
            log_url += ("&" if "?" in log_url else "?") + "limit=10000"
        source = f"`{log_url}`"
        origin = "the backend at that URL"
        kind = "Backend"
    else:
        log_url = f"{args.bridge}/__bridge__/log?limit=10000"
        source = "the bridge"
        origin = "the bridge to huggingface.co"
        kind = "Bridge"
    with urllib.request.urlopen(log_url, timeout=30) as response:
        entries = redact(json.load(response))

    with open(args.out_json, "w") as handle:
        json.dump(entries, handle, indent=1, ensure_ascii=False)
        handle.write("\n")

    writes = sum(1 for e in entries if e["method"] not in ("GET", "HEAD"))
    lines = [
        f"# {kind} exchange log: {args.title}",
        "",
        f"{len(entries)} requests ({writes} state-changing), exported from {source} by "
        "`harness/kb/bridge_log_to_md.py`. Every request below was fired by the web UI (or script) through "
        f"{origin}. E-mails redacted. Do not hand-edit.",
        "",
        "| # | time (UTC) | persona | request | body | status | X-Error-Message / response |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        body = json.dumps(e.get("request_body"), ensure_ascii=False) if e.get("request_body") is not None else ""
        message = (e.get("response_headers") or {}).get("X-Error-Message")
        if message is None:
            response_body = e.get("response_body")
            message = json.dumps(response_body, ensure_ascii=False)[:80] if response_body not in (None, "") else ""
        path = e["path"] + (f"?{e['query']}" if e.get("query") else "")
        lines.append(
            f"| {e['id']} | {e['started_at'][11:23]} | {e['persona']} | `{e['method']} {path}` | "
            f"{body.replace('|', '\\|')} | {e['status']} | {message.replace('|', '\\|')} |"
        )
    with open(args.out_md, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"{len(entries)} entries ({writes} writes) -> {args.out_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
