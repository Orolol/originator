#!/usr/bin/env python3
"""Export the bridge exchange log as a redacted fixture: "which requests did this session fire?".

Fetches `GET /__bridge__/log` from a running bridge and writes JSON + a Markdown table. E-mail
addresses are redacted (the bridge already never logs tokens). Use it right after a scripted or
manual UI walkthrough; clear the log (`DELETE /__bridge__/log`) before starting the walkthrough.

    python3 harness/kb/bridge_log_to_md.py --title "UI walkthrough" \
        --out-json docs/hf-gated/observations/2026-10-05-ui-walkthrough.json \
        --out-md docs/hf-gated/observations/2026-10-05-ui-walkthrough.md
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
    parser.add_argument("--title", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args()

    with urllib.request.urlopen(f"{args.bridge}/__bridge__/log?limit=10000", timeout=30) as response:
        entries = redact(json.load(response))

    with open(args.out_json, "w") as handle:
        json.dump(entries, handle, indent=1, ensure_ascii=False)
        handle.write("\n")

    writes = sum(1 for e in entries if e["method"] not in ("GET", "HEAD"))
    lines = [
        f"# Bridge exchange log: {args.title}",
        "",
        f"{len(entries)} requests ({writes} state-changing), exported from the bridge by "
        "`harness/kb/bridge_log_to_md.py`. Every request below was fired by the web UI (or script) through "
        "the bridge to huggingface.co. E-mails redacted. Do not hand-edit.",
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
