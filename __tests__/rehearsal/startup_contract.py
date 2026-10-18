"""Real loopback bind/TLS control: startup must not need hostname resolution."""

from pathlib import Path
import subprocess
import ssl
import tempfile
from unittest.mock import patch

from fake_eapi import Fake


with tempfile.TemporaryDirectory(prefix="rehearsal-bind-contract-") as temp:
    cert = Path(temp) / "ca.crt"
    key = Path(temp) / "ca.key"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=Offline rehearsal",
            "-addext",
            "subjectAltName=IP:127.0.0.1",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
    )
    with patch(
        "socket.getfqdn", side_effect=AssertionError("hostname resolution attempted")
    ):
        server = Fake(str(cert), str(key))
        try:
            assert server.server_port > 0
            assert isinstance(server.socket, ssl.SSLSocket)
        finally:
            server.server_close()
print("Real numeric loopback bind and TLS succeeded without hostname resolution")
