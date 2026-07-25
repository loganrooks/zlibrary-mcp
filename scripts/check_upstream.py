#!/usr/bin/env python3
"""Probe the third-party surfaces this server depends on.

Two audiences:

* CI — `--github-output` emits a `failed` flag and a `report` block consumed by
  `.github/workflows/upstream-check.yml`, which files an issue on drift.
* Users — `npm run doctor` runs this to answer "is it me or is it them?" before
  filing a bug. Every capability here rides on undocumented endpoints that
  rotate domains without notice, so "the server is broken" and "the upstream
  moved" look identical from a client.

No credentials are required: the probe checks reachability and response shape,
not authenticated behaviour. Authenticated coverage lives in the
`integration`-marked pytest suite.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

# Import the runtime defaults directly from lib/sources/config.py so the probe
# cannot drift from what the server actually contacts (it previously hardcoded
# copies that went stale).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "zlibrary" / "src"))
from lib.sources.config import get_source_config  # noqa: E402
from zlibrary.eapi import DEFAULT_EAPI_DOMAINS, WALLED_STATUS_CODES  # noqa: E402

TIMEOUT = httpx.Timeout(20.0, connect=10.0)

_source_config = get_source_config()

# Mirrors the runtime resolution in lib/python_bridge.py: an explicit
# ZLIBRARY_EAPI_DOMAIN wins; otherwise the runtime probes DEFAULT_EAPI_DOMAINS
# in order and the doctor checks the first candidate (importing the list so
# the probe cannot drift from what the server actually contacts).
ZLIB_DOMAIN = os.environ.get("ZLIBRARY_EAPI_DOMAIN", DEFAULT_EAPI_DOMAINS[0])
# get_source_config() already applies the ANNAS_BASE_URL / LIBGEN_MIRROR
# environment overrides, same as the runtime adapters.
ANNAS_BASE_URL = _source_config.annas_base_url
# LibgenSearch(mirror=suffix) builds https://libgen.{suffix}/ (see
# lib/sources/libgen.py and libgen_api_enhanced) — mirror that construction so
# the probe checks the host the runtime actually contacts.
LIBGEN_BASE_URL = f"https://libgen.{_source_config.libgen_mirror}"

# Markers of domain-parking/traffic-monetization pages. A lapsed mirror that a
# squatter re-registered (e.g. annas-archive.li -> Trellian/Above.com in
# 2026-03) still returns HTTP 200, so "no /md5/ links" alone under-reports what
# happened.
PARKING_MARKERS = (
    "above.com",
    "abovedomains",
    "trellian",
    "tr_uuid=",
    "fingerprintjs",
)


@dataclass
class ProbeResult:
    name: str
    ok: bool
    detail: str
    required: bool = True
    # A network-level refusal (anti-bot wall, datacenter-IP block). Not drift:
    # the upstream contract may be perfectly intact for clients the wall lets
    # through, so a blocked probe must not trigger the drift issue.
    blocked: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def symbol(self) -> str:
        if self.ok:
            return "OK"
        if self.blocked:
            return "BLOCK"
        return "FAIL" if self.required else "WARN"


def _block_detail(resp: httpx.Response) -> Optional[str]:
    """Detect a network-level block in a response, returning a report line.

    Covers the DiamWall anti-bot wall (307 self-redirect setting a `__diamwall`
    cookie, then 513/517 "Access Denied" pages built from cdn.diamwall.com
    assets — ISSUE-API-002) and plain IP-reputation blocking (bare 403, which
    is what GitHub-hosted runners get from every Z-Library domain).

    A probe from a blocked network cannot distinguish "this IP is refused"
    from "the wall is up for everyone" — only a probe from a residential
    network (a user running `npm run doctor`) can. So the detail says both.
    """
    body_is_diamwall = "diamwall" in resp.text.lower()
    if not body_is_diamwall and resp.status_code not in WALLED_STATUS_CODES:
        return None
    wall = "DiamWall anti-bot wall" if body_is_diamwall else "network-level block"
    return (
        f"{wall} (HTTP {resp.status_code}) — {ZLIB_DOMAIN} refuses this "
        "network's clients. From a datacenter/CI address this is expected IP "
        "blocking, not upstream drift. From a residential network, "
        "export ZLIBRARY_EAPI_DOMAIN=<working-domain> (e.g. z-library.ec) "
        "or unset it to use the fallback list"
    )


async def probe_zlibrary_eapi(client: httpx.AsyncClient) -> list[ProbeResult]:
    """Check the EAPI domain-discovery endpoint and the search endpoint's shape."""
    results: list[ProbeResult] = []
    base = f"https://{ZLIB_DOMAIN}"

    try:
        resp = await client.get(f"{base}/eapi/info/domains")
        walled = _block_detail(resp)
        if walled:
            results.append(
                ProbeResult(
                    name="zlibrary:eapi/info/domains",
                    ok=False,
                    detail=walled,
                    blocked=True,
                )
            )
        else:
            resp.raise_for_status()
            payload = resp.json()
            domains = payload.get("domains") or []
            results.append(
                ProbeResult(
                    name="zlibrary:eapi/info/domains",
                    ok=bool(domains),
                    detail=(
                        f"{len(domains)} domain(s) advertised: {', '.join(map(str, domains[:3]))}"
                        if domains
                        else "endpoint reachable but advertised no domains "
                        "(contract change — domain discovery drives every later call)"
                    ),
                    extra={"domains": domains[:5]},
                )
            )
    except Exception as exc:  # noqa: BLE001 - any failure is a reportable signal
        results.append(
            ProbeResult(
                name="zlibrary:eapi/info/domains",
                ok=False,
                detail=f"{type(exc).__name__}: {exc}",
            )
        )

    try:
        # An unauthenticated search still exercises the JSON contract: a Cloudflare
        # interstitial or an HTML error page fails to parse, which is the signal.
        resp = await client.post(
            f"{base}/eapi/book/search",
            data={"message": "philosophy", "limit": "1", "page": "1"},
        )
        walled = _block_detail(resp)
        if walled:
            results.append(
                ProbeResult(
                    name="zlibrary:eapi/book/search",
                    ok=False,
                    detail=walled,
                    blocked=True,
                )
            )
            return results
        resp.raise_for_status()
        payload = resp.json()
        has_shape = isinstance(payload, dict) and (
            "books" in payload or "success" in payload
        )
        results.append(
            ProbeResult(
                name="zlibrary:eapi/book/search",
                ok=has_shape,
                detail=(
                    f"JSON response with keys: {sorted(payload)[:6]}"
                    if has_shape
                    else f"unexpected response shape: {str(payload)[:200]}"
                ),
            )
        )
    except Exception as exc:  # noqa: BLE001
        results.append(
            ProbeResult(
                name="zlibrary:eapi/book/search",
                ok=False,
                detail=f"{type(exc).__name__}: {exc}",
            )
        )

    return results


async def probe_annas(client: httpx.AsyncClient) -> ProbeResult:
    """Anna's Archive is HTML-scraped, so reachability alone is worth reporting."""
    try:
        resp = await client.get(f"{ANNAS_BASE_URL}/search", params={"q": "philosophy"})
        resp.raise_for_status()
        body = resp.text
        # The adapter keys off result anchors; their absence means either a layout
        # change, a block page, or a parked domain.
        looks_like_results = "/md5/" in body
        if looks_like_results:
            detail = "search page contains /md5/ result links"
        else:
            lower_body = body.lower()
            parked = any(marker in lower_body for marker in PARKING_MARKERS)
            detail = (
                "domain appears PARKED (squatter/traffic-monetization page) — "
                "the configured base URL no longer belongs to Anna's Archive; "
                "update ANNAS_BASE_URL / lib/sources/config.py"
                if parked
                else "reachable but no /md5/ links found "
                "(layout change or block page — the HTML adapter will return nothing)"
            )
        return ProbeResult(
            name="annas-archive:search",
            ok=looks_like_results,
            detail=detail,
            # Anna's is optional: the router falls back to LibGen without a key.
            required=False,
        )
    except Exception as exc:  # noqa: BLE001
        return ProbeResult(
            name="annas-archive:search",
            ok=False,
            detail=f"{type(exc).__name__}: {exc}",
            required=False,
        )


async def probe_libgen(client: httpx.AsyncClient) -> ProbeResult:
    """LibGen is the router's fallback source; mirrors rotate frequently."""
    try:
        # The li-family mirrors serve search at /index.php (search.php 404s).
        resp = await client.get(
            f"{LIBGEN_BASE_URL}/index.php", params={"req": "python"}
        )
        resp.raise_for_status()
        return ProbeResult(
            name="libgen:search",
            ok=resp.status_code == 200 and len(resp.text) > 500,
            detail=f"HTTP {resp.status_code}, {len(resp.text)} bytes",
            required=False,
        )
    except Exception as exc:  # noqa: BLE001
        return ProbeResult(
            name="libgen:search",
            ok=False,
            detail=f"{type(exc).__name__}: {exc}",
            required=False,
        )


async def run_probes() -> list[ProbeResult]:
    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "zlibrary-mcp-upstream-check"},
    ) as client:
        zlib_results, annas, libgen = await asyncio.gather(
            probe_zlibrary_eapi(client),
            probe_annas(client),
            probe_libgen(client),
        )
    return [*zlib_results, annas, libgen]


def actionable_failures(results: list[ProbeResult]) -> list[ProbeResult]:
    """Failures that indicate drift a maintainer can act on.

    Blocked probes are excluded: an IP-level refusal says nothing about the
    upstream contract, and counting it would keep the drift issue permanently
    open from CI's datacenter address.
    """
    return [r for r in results if r.required and not r.ok and not r.blocked]


def render(results: list[ProbeResult]) -> str:
    width = max(len(r.name) for r in results)
    lines = [f"{r.symbol:<5} {r.name:<{width}}  {r.detail}" for r in results]
    required_failures = actionable_failures(results)
    optional_failures = [
        r for r in results if not r.required and not r.ok and not r.blocked
    ]
    blocked = [r for r in results if r.blocked]
    lines.append("")
    summary = (
        f"{sum(1 for r in results if r.ok)} passing, "
        f"{len(required_failures)} required failing, "
        f"{len(optional_failures)} optional failing"
    )
    if blocked:
        summary += f", {len(blocked)} blocked (network-level, not drift)"
    lines.append(summary)
    return "\n".join(lines)


def emit_github_output(report: str, failed: bool, zlib_blocked: bool = False) -> None:
    path: Optional[str] = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"failed={'true' if failed else 'false'}\n")
        # The live-suite job gates on this: logging in through a wall would
        # both fail spuriously and burn the ~10/hour login rate limit.
        handle.write(f"zlib_blocked={'true' if zlib_blocked else 'false'}\n")
        # Heredoc form so multi-line reports survive intact.
        handle.write("report<<PROBE_EOF\n")
        handle.write(report + "\n")
        handle.write("PROBE_EOF\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON instead of text"
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="also write failed/report to $GITHUB_OUTPUT",
    )
    args = parser.parse_args()

    results = asyncio.run(run_probes())
    required_failed = bool(actionable_failures(results))
    zlib_blocked = any(r.blocked for r in results)

    if args.json:
        print(
            json.dumps(
                {
                    "failed": required_failed,
                    "zlib_blocked": zlib_blocked,
                    "results": [
                        {
                            "name": r.name,
                            "ok": r.ok,
                            "required": r.required,
                            "blocked": r.blocked,
                            "detail": r.detail,
                            **r.extra,
                        }
                        for r in results
                    ],
                },
                indent=2,
            )
        )
    else:
        print(render(results))

    if args.github_output:
        emit_github_output(render(results), required_failed, zlib_blocked)

    # Required-source failure is an actionable signal; optional-source failure is not.
    return 1 if required_failed else 0


if __name__ == "__main__":
    sys.exit(main())
