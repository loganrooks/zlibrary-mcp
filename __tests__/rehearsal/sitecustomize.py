"""Test-process-only network fence, loaded through this harness's PYTHONPATH."""

import ipaddress
import socket
import os

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_original_getaddrinfo = socket.getaddrinfo


def _check(address):
    if not isinstance(address, tuple):
        return  # Unix-domain sockets do not reach the network.
    try:
        allowed = str(ipaddress.ip_address(address[0])) == "127.0.0.1"
    except ValueError:
        allowed = False
    allowed = allowed and str(address[1]) == os.environ.get("REHEARSAL_ALLOWED_PORT")
    if not allowed:
        with open(os.environ["REHEARSAL_EGRESS_TRAP"], "a") as trap:
            trap.write("blocked outbound attempt\n")
        raise RuntimeError("rehearsal blocked non-loopback network access")


def _connect(self, address):
    _check(address)
    return _original_connect(self, address)


def _connect_ex(self, address):
    _check(address)
    return _original_connect_ex(self, address)


def _getaddrinfo(host, port, *args, **kwargs):
    _check((host, port))
    return _original_getaddrinfo(host, port, *args, **kwargs)


socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex
socket.getaddrinfo = _getaddrinfo

# URL-only seam for the real LibGen library's internally constructed domain.
# Keep requests, TLS, parsing and the production bridge real. No other URL is rewritten.
if os.environ.get("REHEARSAL_LIBGEN_ORIGIN"):
    from urllib.parse import urlsplit
    import requests
    import httpx

    def _fixture_url(url):
        parsed = urlsplit(str(url))
        if parsed.hostname not in {"libgen.li", "libgen.vg", "libgen.la"}:
            return None
        target = os.environ["REHEARSAL_LIBGEN_ORIGIN"] + "/libgen" + parsed.path
        if parsed.query:
            target += "?" + parsed.query
        return target

    _request = requests.Session.request

    def _fixture_request(self, method, url, *args, **kwargs):
        target = _fixture_url(url)
        if target:
            url = target
            kwargs["verify"] = os.environ["SSL_CERT_FILE"]
        return _request(self, method, url, *args, **kwargs)

    requests.Session.request = _fixture_request

    # Resolver and streamed transfers use httpx, unlike the search library.
    # Rewrite only the URL; keep the real TLS, HTTP and streaming stack.
    _send = httpx.AsyncClient.send

    async def _fixture_send(self, request, *args, **kwargs):
        target = _fixture_url(request.url)
        if target:
            request.url = httpx.URL(target)
            request.headers["Host"] = request.url.netloc.decode("ascii")
        return await _send(self, request, *args, **kwargs)

    httpx.AsyncClient.send = _fixture_send
