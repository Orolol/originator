#!/usr/bin/env python3
"""Diff two exchange logs in the bridge-log schema (`/__bridge__/log`, `/__clone__/log`) as Markdown.

Typical use: the *reference* is the log of a live session recorded through the bridge, the
*candidate* is the log of the same scripted session against the clone. Stdlib only.

    python3 harness/kb/compare_logs.py \
        docs/hf-gated/observations/2026-10-05-ui-walkthrough.json web/e2e/out/clone-walkthrough-log.json \
        --out-md web/e2e/out/clone-vs-live.md

What is compared (everything else, such as `id`, `started_at`, `duration_ms`, `upstream`, is ignored;
the clone's timestamps are virtual-clock values):

1. State-changing requests (every method except GET and HEAD), as an **ordered sequence**, paired by
   position: persona, method, path, query, request body, response status and response body must be
   equal. This is the pass criterion. Response headers are compared too, but only informationally
   (Content-Type, ETag, Location with its origin stripped, X-Error-*, WWW-Authenticate).
2. GET and HEAD requests, as a **multiset** of (persona, method, path[?query], status): order is
   ignored, and the counts may legitimately differ (retries, refetch timing). Differences are
   reported but do not fail the run unless `--strict-gets` is given.

E-mail addresses are replaced by `<email>` in both logs before comparing (recordings are redacted,
the clone's own addresses are not). Exit status: 0 = state-changing sequences identical (and, with
`--strict-gets`, GET multisets equal), 1 = a difference, 2 = unreadable input.
"""

import argparse
import json
import re
import sys
from collections import Counter
from urllib.parse import urlsplit

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
READS = ("GET", "HEAD")
# Compared as informational only: a clone is allowed to differ on headers the web app drops anyway.
INFO_HEADERS = ("content-type", "etag", "location", "x-error-code", "x-error-message", "www-authenticate")
WRITE_FIELDS = ("persona", "method", "path", "query", "request_body", "status", "response_body")


def redact(node):
    if isinstance(node, dict):
        return {k: redact(v) for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v) for v in node]
    if isinstance(node, str):
        return EMAIL.sub("<email>", node)
    return node


def load(path: str) -> list[dict]:
    try:
        with open(path) as handle:
            entries = json.load(handle)
    except (OSError, ValueError) as exc:
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(entries, list) or not all(isinstance(e, dict) and "method" in e for e in entries):
        print(f"{path}: not a list of exchange-log entries", file=sys.stderr)
        raise SystemExit(2)
    return redact(entries)


def cell(value, limit: int = 90) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = text if len(text) <= limit else text[: limit - 1] + "…"
    return text.replace("|", "\\|").replace("\n", " ")


def code(value) -> str:
    return f"`{cell(value)}`" if value not in (None, "") else ""


def request_line(entry: dict) -> str:
    query = f"?{entry['query']}" if entry.get("query") else ""
    return f"{entry['method']} {entry['path']}{query}"


def info_headers(entry: dict) -> dict:
    headers = {k.lower(): v for k, v in (entry.get("response_headers") or {}).items() if k.lower() in INFO_HEADERS}
    if "location" in headers:
        parts = urlsplit(headers["location"])
        headers["location"] = parts.path + (f"?{parts.query}" if parts.query else "")
    return headers


def compare_writes(ref: list[dict], cand: list[dict]):
    """Pairs by position; returns rows [(ref_entry|None, cand_entry|None, [field diffs], [header diffs])]."""
    rows = []
    for i in range(max(len(ref), len(cand))):
        a = ref[i] if i < len(ref) else None
        b = cand[i] if i < len(cand) else None
        diffs, header_diffs = [], []
        if a is not None and b is not None:
            diffs = [f for f in WRITE_FIELDS if a.get(f) != b.get(f)]
            ha, hb = info_headers(a), info_headers(b)
            header_diffs = [h for h in sorted(ha.keys() | hb.keys()) if ha.get(h) != hb.get(h)]
        rows.append((a, b, diffs, header_diffs))
    return rows


def read_key(entry: dict) -> tuple:
    return (entry["persona"], entry["method"], request_line(entry).split(" ", 1)[1], entry["status"])


def render(ref, cand, ref_label, cand_label, notes: str | None, ref_path: str, cand_path: str):
    ref_writes = [e for e in ref if e["method"] not in READS]
    cand_writes = [e for e in cand if e["method"] not in READS]
    ref_reads = Counter(read_key(e) for e in ref if e["method"] in READS)
    cand_reads = Counter(read_key(e) for e in cand if e["method"] in READS)

    rows = compare_writes(ref_writes, cand_writes)
    identical = sum(1 for a, b, d, _ in rows if a is not None and b is not None and not d)
    total = max(len(ref_writes), len(cand_writes))
    write_ok = identical == total and len(ref_writes) == len(cand_writes)

    keys = sorted(ref_reads.keys() | cand_reads.keys(), key=lambda k: (k[0], k[2], k[1], k[3]))
    read_diffs = [k for k in keys if ref_reads[k] != cand_reads[k]]
    reads_ok = not read_diffs

    out = [
        f"# Log diff: {cand_label} vs {ref_label}",
        "",
        f"Reference ({ref_label}): `{ref_path}`, {len(ref)} requests ({len(ref_writes)} state-changing). "
        f"Candidate ({cand_label}): `{cand_path}`, {len(cand)} requests ({len(cand_writes)} state-changing). "
        "Generated by `harness/kb/compare_logs.py`; e-mails redacted to `<email>`; `id`, `started_at` "
        "(virtual clock on the clone), `duration_ms` and `upstream` ignored.",
        "",
        "## Summary",
        "",
        f"- State-changing requests, ordered: **{identical}/{total} identical** "
        f"({len(ref_writes)} in {ref_label}, {len(cand_writes)} in {cand_label}) "
        f"{'PASS' if write_ok else 'FAIL'}.",
        f"- GET/HEAD requests, multiset of (persona, method, path, status): {sum(ref_reads.values())} in "
        f"{ref_label}, {sum(cand_reads.values())} in {cand_label}; "
        + ("**equal**." if reads_ok else f"**{len(read_diffs)} key(s) differ** (see below)."),
        "",
        "## 1. State-changing requests (ordered, exact match required)",
        "",
        "Compared fields: persona, method, path, query, request body, response status, response body.",
        "",
        "| # | persona | request | body | status | response | match |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, (a, b, diffs, header_diffs) in enumerate(rows, 1):
        shown = a if a is not None else b
        verdict = "identical" if a is not None and b is not None and not diffs else (
            f"**DIFF** ({', '.join(diffs)})" if diffs else f"**only in {ref_label if b is None else cand_label}**"
        )
        out.append(
            f"| {i} | {shown['persona']} | `{request_line(shown)}` | {code(shown.get('request_body'))} | "
            f"{shown['status']} | {code(shown.get('response_body'))} | {verdict} |"
        )
    mismatches = [(i, a, b, d) for i, (a, b, d, _) in enumerate(rows, 1) if d or a is None or b is None]
    if mismatches:
        out += ["", "### Differences", ""]
        for i, a, b, d in mismatches:
            out.append(f"**#{i}**")
            for label, entry in ((ref_label, a), (cand_label, b)):
                if entry is None:
                    out.append(f"- {label}: (no request)")
                else:
                    out.append(
                        f"- {label}: `{request_line(entry)}` persona={entry['persona']} "
                        f"body={cell(entry.get('request_body'), 200)!r} status={entry['status']} "
                        f"response={cell(entry.get('response_body'), 300)!r}"
                    )
            out.append("")
    header_rows = [(i, a, b, h) for i, (a, b, _, h) in enumerate(rows, 1) if h]
    out += ["", "Response headers (informational, not part of the pass criterion): "
            + ("identical on every pair." if not header_rows else "differences below."), ""]
    for i, a, b, h in header_rows:
        ha, hb = info_headers(a), info_headers(b)
        for name in h:
            out.append(f"- #{i} `{name}`: {ref_label} `{ha.get(name)}` / {cand_label} `{hb.get(name)}`")

    out += [
        "",
        "## 2. GET / HEAD requests (multiset, order ignored)",
        "",
        "Compared as a multiset of (persona, method, path[?query], status). Order is ignored: requests fired "
        "concurrently (a page's server-side fetches, the three list refetches) reach the backend in a "
        "non-deterministic order on both sides, and counts may differ legitimately (retries, refetch timing).",
        "",
        "| persona | request | status | " + f"{ref_label} | {cand_label} | diff |",
        "|---|---|---|---|---|---|",
    ]
    for key in keys:
        persona, method, path, status = key
        delta = cand_reads[key] - ref_reads[key]
        out.append(
            f"| {persona} | `{method} {path}` | {status} | {ref_reads[key]} | {cand_reads[key]} | "
            f"{'' if delta == 0 else f'{delta:+d}'} |"
        )
    out += ["", f"{len(keys) - len(read_diffs)}/{len(keys)} distinct keys have equal counts."]
    if notes:
        out += ["", "## Notes", "", notes.rstrip()]
    return "\n".join(out) + "\n", write_ok, reads_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("reference", help="reference log (JSON list), e.g. the live recording")
    parser.add_argument("candidate", help="candidate log (JSON list), e.g. the clone's export")
    parser.add_argument("--reference-label", default="live")
    parser.add_argument("--candidate-label", default="clone")
    parser.add_argument("--out-md", help="write the Markdown report here (default: stdout)")
    parser.add_argument("--notes", help="Markdown file appended verbatim as a `## Notes` section")
    parser.add_argument("--strict-gets", action="store_true", help="also fail (exit 1) when the GET/HEAD multisets differ")
    args = parser.parse_args()

    notes = None
    if args.notes:
        with open(args.notes) as handle:
            notes = handle.read()
    report, write_ok, reads_ok = render(
        load(args.reference), load(args.candidate), args.reference_label, args.candidate_label, notes,
        args.reference, args.candidate,
    )
    if args.out_md:
        with open(args.out_md, "w") as handle:
            handle.write(report)
    else:
        sys.stdout.write(report)
    summary = report.split("## Summary\n\n", 1)[1].split("\n\n##", 1)[0]
    print(summary, file=sys.stderr)
    return 0 if write_ok and (reads_ok or not args.strict_gets) else 1


if __name__ == "__main__":
    sys.exit(main())
