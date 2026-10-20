"""Run with the image's Python and MCP container environment before the journey."""

import socket

try:
    # RFC 5737 documentation address. The fence must reject this BEFORE any
    # syscall; a kernel/network failure alone does not qualify the canary.
    socket.create_connection(("203.0.113.1", 443), timeout=1)
except RuntimeError as error:
    assert str(error) == "rehearsal blocked non-loopback network access"
else:
    raise AssertionError("canary connection must be blocked by the rehearsal fence")
