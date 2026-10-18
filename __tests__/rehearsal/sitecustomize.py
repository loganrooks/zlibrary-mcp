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
