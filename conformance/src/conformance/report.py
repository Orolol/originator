"""`conformance-report`: replay every recording against the backend and write a diff report.

    uv run --project conformance conformance-report                       # clone on :8200
    uv run --project conformance conformance-report --pytest              # + rule/client tests
    BACKEND_URL=http://127.0.0.1:8100 uv run --project conformance conformance-report --live   # GET/HEAD only

Writes conformance/reports/latest.{json,md} (live: reports/live.{json,md}). Exit code 1 when any
scenario has a mismatch that divergences.yaml does not list, or when --pytest fails.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from .compare import NORMALISATIONS
from .config import CONFORMANCE, REPORTS, backend_url
from .divergences import load_divergences
from .replay import ScenarioResult, live_scenario_names, load_manifest, make_client, run_scenario, scenario_names


def _md_cell(value: object, limit: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = text.replace("\n", "\\n").replace("|", "\\|")
    return text if len(text) <= limit else text[:limit] + "…"


def run_pytest(backend: str) -> dict:
    junit = REPORTS / "pytest.xml"
    env = {**os.environ, "BACKEND_URL": backend}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(CONFORMANCE / "tests"), "-q", "-p", "no:cacheprovider",
         f"--junitxml={junit}"],
        cwd=CONFORMANCE, env=env, capture_output=True, text=True,
    )
    tests = []
    if junit.exists():
        for case in ET.parse(junit).getroot().iter("testcase"):
            outcome, message = "passed", ""
            for tag in ("failure", "error", "skipped"):
                node = case.find(tag)
                if node is not None:
                    outcome = {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
                    if tag == "skipped" and node.get("type") == "pytest.xfail":
                        outcome = "xfailed"
                    message = (node.get("message") or "").strip()
                    break
            tests.append({"file": case.get("classname"), "name": case.get("name"), "outcome": outcome,
                          "message": message})
    return {"exit_code": proc.returncode, "tail": proc.stdout[-3000:], "tests": tests}


def build_markdown(results: list[ScenarioResult], backend: str, generated: str, pytest_result: dict | None) -> str:
    divergences = load_divergences()
    manifest = load_manifest()
    lines = [
        "# Conformance report: clone vs real-Hub recordings",
        "",
        f"Generated {generated} against `{backend}` by `conformance-report` (conformance/). "
        "Ground truth: `docs/hf-gated/observations/2026-10-05-*.json`. Expectations come from the "
        "recordings and the KB only (the suite never reads the clone's code). Reproduce with "
        "`uv run --project conformance conformance-report --pytest` (clone on :8200).",
        "",
        "## Summary",
        "",
        "| scenario | recording | steps | pass | diverged (listed) | fail | skipped | error | result |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for result in results:
        c = result.counts()
        verdict = "ERROR" if result.error else ("PASS" if result.ok else "FAIL")
        note = " (stand-ins)" if result.stand_ins else ""
        lines.append(
            f"| {result.name}{note} | `{result.recording}` | {len(result.steps)} | {c['pass']} | {c['diverged']} "
            f"| {c['fail']} | {c['skipped']} | {c['error']} | **{verdict}** |"
        )
    lines.append("")
    errors = [r for r in results if r.error]
    if errors:
        lines += ["## Scenario errors", ""]
        lines += [f"- **{r.name}**: `{_md_cell(r.error, 600)}`" for r in errors]
        lines.append("")

    lines += ["## Unexpected mismatches (verbatim)", ""]
    any_unexpected = False
    for result in results:
        unexpected = [r for r in result.steps if r.outcome in ("fail", "error")]
        if not unexpected:
            continue
        any_unexpected = True
        lines += [f"### {result.name}", "", "| step | request | field | expected (recording) | actual (backend) | detail |",
                  "|---|---|---|---|---|---|"]
        for step_result in unexpected:
            s = step_result.step
            request = f"{s.persona} {s.method} {s.path}"
            if step_result.outcome == "error":
                lines.append(f"| {s.id} | `{_md_cell(request)}` | transport | | | {_md_cell(step_result.reason)} |")
                continue
            for diff in step_result.diffs:
                if diff.divergence:
                    continue
                lines.append(
                    f"| {s.id} | `{_md_cell(request, 90)}` | `{diff.field}` | `{_md_cell(diff.expected)}` "
                    f"| `{_md_cell(diff.actual)}` | {_md_cell(diff.detail)} |"
                )
        lines.append("")
    if not any_unexpected:
        lines += ["None.", ""]

    from fnmatch import fnmatchcase

    run_names = [r.name for r in results]
    used: dict[str, int] = {}
    for result in results:
        for step_result in result.steps:
            for diff in step_result.diffs:
                if diff.divergence:
                    used[diff.divergence] = used.get(diff.divergence, 0) + 1
    lines += ["## Listed divergences (conformance/divergences.yaml)", ""]
    if divergences:
        lines += ["| id | scenario / step / field | rule | reason | diffs covered |", "|---|---|---|---|---|"]
        for entry in divergences:
            if entry.scenario.startswith("rules:"):
                covered = "pytest strict xfail"
            elif not any(fnmatchcase(name, entry.scenario) for name in run_names):
                covered = "n/a (scenario not run)"
            else:
                covered = used.get(entry.id, 0) or "none (stale?)"
            lines.append(f"| {entry.id} | `{entry.scenario}` / `{_md_cell(entry.step)}` / `{_md_cell(entry.field)}` "
                         f"| {entry.rule} | {_md_cell(entry.reason, 400)} | {covered} |")
    else:
        lines.append("None listed.")
    lines.append("")

    lines += ["## Scope restrictions", "",
              "Steps not replayed, or compared on a subset of fields, and why (from `conformance/scenarios.yaml`).", ""]
    for name, spec in manifest["scenarios"].items():
        for step, reason in (spec.get("skip") or {}).items():
            lines.append(f"- {name} / `{step}`: skipped. {reason}")
        for step, rule in (spec.get("compare_only") or {}).items():
            lines.append(f"- {name} / `{step}`: only {', '.join(f'`{f}`' for f in rule['fields'])}. {rule['reason']}")
    lines += ["- Stand-in repos (`meta-llama/Llama-3.2-1B`, `bigcode/starcoder`, `mistralai/Mistral-7B-v0.1`, "
              "`openai-community/gpt2`) are seeded locally with the recorded ids, `_id` and `gated`; their file "
              "contents are stubs (the recorded 160-character excerpt), so for them only status, error headers, "
              "content type and allowlist decisions carry evidence.", ""]

    lines += ["## Normalisations", ""]
    lines += [f"- **{title}**: {text}" for title, text in NORMALISATIONS]
    lines.append("")

    if pytest_result is not None:
        tests = pytest_result["tests"]
        by_file: dict[str, dict[str, int]] = {}
        for test in tests:
            counts = by_file.setdefault(test["file"], {"passed": 0, "failed": 0, "error": 0, "xfailed": 0, "skipped": 0})
            counts[test["outcome"]] += 1
        lines += ["## Rule, provisional and client tests (pytest)", "",
                  f"pytest exit code {pytest_result['exit_code']}.", "",
                  "| module | passed | failed | error | xfailed (listed divergence) | skipped |", "|---|---|---|---|---|---|"]
        for module, c in sorted(by_file.items()):
            lines.append(f"| `{module}` | {c['passed']} | {c['failed']} | {c['error']} | {c['xfailed']} | {c['skipped']} |")
        failing = [t for t in tests if t["outcome"] in ("failed", "error")]
        if failing:
            lines += ["", "Failing tests:", ""]
            lines += [f"- `{t['file']}::{t['name']}`: {_md_cell(t['message'], 500)}" for t in failing]
        xfailed = [t for t in tests if t["outcome"] == "xfailed"]
        if xfailed:
            lines += ["", "Known divergences (strict xfail, see divergences.yaml):", ""]
            lines += [f"- `{t['file']}::{t['name']}`: {_md_cell(t['message'], 300)}" for t in xfailed]
        lines.append("")

    lines += ["## Per-step detail", ""]
    for result in results:
        lines += [f"### {result.name}", "", f"Covers: {', '.join(result.covers)}.", "",
                  "| step | persona | request | status rec → backend | outcome | notes |", "|---|---|---|---|---|---|"]
        for step_result in result.steps:
            s = step_result.step
            notes = step_result.reason
            if step_result.diffs:
                notes = "; ".join(
                    f"{d.field}{' [' + d.divergence + ']' if d.divergence else ''}" for d in step_result.diffs[:6]
                ) + (f"; +{len(step_result.diffs) - 6} more" if len(step_result.diffs) > 6 else "")
            actual = step_result.actual_status if step_result.actual_status is not None else "—"
            lines.append(f"| {s.id} | {s.persona} | `{_md_cell(s.method + ' ' + s.path, 100)}` "
                         f"| {s.expected.status} → {actual} | {step_result.outcome} | {_md_cell(notes, 300)} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", default=None, help="backend URL (default: $BACKEND_URL or http://127.0.0.1:8200)")
    parser.add_argument("--out", default=None,
                        help="output path without extension (default: reports/latest, or reports/live with --live)")
    parser.add_argument("--scenario", action="append", help="only these scenarios (repeatable)")
    parser.add_argument("--live", action="store_true", help="read-only replay against the bridge, no seeding")
    parser.add_argument("--pytest", action="store_true", help="also run the pytest suite and include its results")
    args = parser.parse_args(argv)

    backend = (args.backend or backend_url()).rstrip("/")
    os.environ["BACKEND_URL"] = backend
    names = args.scenario or (live_scenario_names() if args.live else scenario_names())
    results = []
    with make_client(backend) as client:
        for name in names:
            results.append(run_scenario(name, client, live=args.live))
    pytest_result = run_pytest(backend) if args.pytest else None
    generated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = Path(args.out or REPORTS / ("live" if args.live else "latest"))
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": generated,
        "backend": backend,
        "mode": "live" if args.live else "seeded",
        "scenarios": [r.as_dict() for r in results],
        "divergences": [vars(d) for d in load_divergences()],
        "normalisations": [{"name": n, "rule": t} for n, t in NORMALISATIONS],
        "pytest": pytest_result,
    }
    out.with_suffix(".json").write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str) + "\n")
    out.with_suffix(".md").write_text(build_markdown(results, backend, generated, pytest_result))
    for result in results:
        c = result.counts()
        verdict = "ERROR " + result.error if result.error else ("PASS" if result.ok else "FAIL")
        print(f"{result.name}: {verdict} (pass {c['pass']}, diverged {c['diverged']}, fail {c['fail']}, "
              f"skipped {c['skipped']}, error {c['error']})")
    if pytest_result is not None:
        print(f"pytest exit code {pytest_result['exit_code']}")
    print(f"report: {out.with_suffix('.md')}")
    failed = any(not r.ok for r in results) or (pytest_result is not None and pytest_result["exit_code"] != 0)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
