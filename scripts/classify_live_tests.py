#!/usr/bin/env python3
"""Classify live pytest results using same-domain reachability evidence.

The workflow captures pytest's exit code and uses these outputs to fail the job
only for real failures. This command itself succeeds after emitting a classified
failure; malformed/missing evidence is a failure, never a block or pass.
"""

import argparse
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET


BLOCK_REASON = (
    "anti-bot wall corroborated by the reachability probe for the same domain"
)


def is_blocked(problem: ET.Element, probe_domain: str, live_domain: str) -> bool:
    """Match the terminal exception, not source/traceback mentions of a wall.

    Called only when the probe reported a block. Setup transport errors also
    require the configured live domain to match; call/teardown errors remain
    actionable. A wall must name the probe domain and the body-marker branch.
    """
    message = problem.get("message", "")
    setup = problem.tag == "error" and message.startswith('failed on setup with "')
    if setup:
        message = message.removeprefix('failed on setup with "').removesuffix('"')
    wall = re.match(
        r"(?:zlibrary\.eapi\.)?DiamWallError: DiamWall anti-bot wall detected on "
        r"([^\s()]+) \(HTTP \d+ DiamWall block page\)",
        message,
    )
    return bool(wall and wall.group(1) == probe_domain) or (
        setup
        and live_domain == probe_domain
        and message.partition(":")[0] in ("httpx.ConnectError", "httpx.ConnectTimeout")
    )


def classify(exit_code: int, report: Path) -> dict[str, object]:
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError):
        return {
            "status": "failed",
            "blocked": False,
            "detail": "Missing/invalid live JUnit report",
        }

    cases = list(root.iter("testcase"))
    problems = [p for p in root.iter() if p.tag in ("error", "failure")]
    probe_domain = os.environ.get("ZLIB_PROBE_DOMAIN", "")
    live_domain = os.environ.get("ZLIBRARY_EAPI_DOMAIN", "")
    probe_blocked = os.environ.get("ZLIB_BLOCKED") == "true" and bool(probe_domain)
    blocked_count = sum(
        probe_blocked and is_blocked(p, probe_domain, live_domain) for p in problems
    )
    failed_count = len(problems) - blocked_count
    # Interruptions, collection errors, usage errors and empty suites cannot be
    # explained away by a block seen elsewhere in a partial report.
    if exit_code == 0 and cases and not problems:
        status = "passed"
    elif exit_code == 1 and blocked_count and not failed_count:
        status = "blocked"
    else:
        status = "failed"
    detail = f"Live suite: {status}; {failed_count} failure(s), {blocked_count} blocked result(s); pytest exit {exit_code}."
    if blocked_count:
        detail += f" Z-Library: {BLOCK_REASON} ({probe_domain})."
    return {"status": status, "blocked": bool(blocked_count), "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--junitxml", type=Path, required=True)
    args = parser.parse_args()
    result = classify(args.exit_code, args.junitxml)
    print(result["detail"])
    if result["blocked"]:
        print(f"::warning::{BLOCK_REASON}")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"status={result['status']}\n")
            handle.write(f"blocked={str(result['blocked']).lower()}\n")
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(str(result["detail"]) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
