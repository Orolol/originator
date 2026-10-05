#!/usr/bin/env python3
"""Extract the slice-relevant part of a target's published OpenAPI spec.

Target-agnostic: point it at any OpenAPI 3.x document, select paths with a regex,
and it writes those operations with every `$ref` resolved inline, so an agent can
read one self-contained file instead of a 1 MB spec.

Usage (HF gated-models slice):
    python3 harness/kb/extract_openapi.py \
        --spec-url https://huggingface.co/.well-known/openapi.json \
        --include 'user-access-request|ask-access|user-access-report|/settings$' \
        --exclude '^/api/(datasets|spaces|buckets|containers|organizations)/|^/datasets/|resource-groups|settings/tokens' \
        --out docs/hf-gated/snapshots/openapi-gated.json

Stdlib only, on purpose: it must run before any project environment exists.
"""

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request


def resolve(node, components, depth=0):
    if depth > 40:
        raise RecursionError("$ref chain too deep; spec is probably recursive here")
    if isinstance(node, dict):
        if set(node) == {"$ref"}:
            target = components
            for key in node["$ref"].split("/")[2:]:  # "#/components/schemas/X"
                target = target[key]
            return resolve(target, components, depth + 1)
        return {k: resolve(v, components, depth + 1) for k, v in node.items() if k != "$schema"}
    if isinstance(node, list):
        return [resolve(v, components, depth + 1) for v in node]
    return node


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec-url", required=True)
    parser.add_argument("--include", required=True, help="regex matched against the path template")
    parser.add_argument("--exclude", default=None, help="regex; matching paths are dropped")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with urllib.request.urlopen(args.spec_url, timeout=60) as response:
        spec = json.load(response)

    include = re.compile(args.include)
    exclude = re.compile(args.exclude) if args.exclude else None
    components = spec.get("components", {})
    paths = {
        path: resolve(ops, components)
        for path, ops in spec["paths"].items()
        if include.search(path) and not (exclude and exclude.search(path))
    }

    snapshot = {
        "_meta": {
            "source": args.spec_url,
            "fetched_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "spec_title": spec.get("info", {}).get("title"),
            "spec_version": spec.get("info", {}).get("version"),
            "include": args.include,
            "exclude": args.exclude,
        },
        "paths": paths,
    }
    with open(args.out, "w") as handle:
        json.dump(snapshot, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print(f"{len(paths)} paths -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
