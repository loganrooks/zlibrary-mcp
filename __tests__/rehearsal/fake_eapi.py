"""Loopback-only EAPI contract double. Never forwards a request upstream."""

from collections import Counter
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import ssl
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

USER_ID = "rehearsal-cookie-id"
USER_KEY = "rehearsal-cookie-key"
MODES = {
    "healthy",
    "login400",
    "unauthorized",
    "profile401",
    "operation401",
    "success0",
    "timeout",
    "wall",
    "slow",
    "ambiguous400",
}


class Fake(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, cert, key):
        super().__init__(("127.0.0.1", 0), Handler)
        self.lock = threading.Lock()
        self.calls = Counter()
        self.mode = "healthy"
        self.epoch = 1
        self.successes = 0
        self.inflight = 0
        self.max_inflight = 0
        self.drop_cookies = False
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        self.socket = context.wrap_socket(self.socket, server_side=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # Request bodies and auth headers must not reach logs.

    def reply(self, payload, status=200, content_type="application/json", headers=None):
        data = (
            json.dumps(payload).encode()
            if content_type == "application/json"
            else payload
        )
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
            pass

    def do_POST(self):
        self.handle_request()

    def do_GET(self):
        self.handle_request()

    def handle_request(self):
        with self.server.lock:
            self.server.inflight += 1
            self.server.max_inflight = max(
                self.server.max_inflight, self.server.inflight
            )
        try:
            self.dispatch_request()
        finally:
            with self.server.lock:
                self.server.inflight -= 1

    def dispatch_request(self):
        route = urlsplit(self.path).path
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if route == "/__mode":
            value = json.loads(body)
            if value.get("mode", "healthy") not in MODES:
                return self.reply({"error": "unknown mode"}, 400)
            with self.server.lock:
                self.server.mode = value.get("mode", "healthy")
                self.server.drop_cookies = value.get("drop_cookies", False)
                if value.get("reject_epoch"):
                    self.server.epoch += 1
                if value.get("reset"):
                    self.server.calls.clear()
                    self.server.epoch = 1
                    self.server.successes = 0
                    self.server.max_inflight = 0
            return self.reply({"ok": True})
        if route == "/__stats":
            with self.server.lock:
                calls = dict(self.server.calls)
            return self.reply(
                {
                    "logins": calls.get("/eapi/user/login", 0),
                    "loginSuccesses": self.server.successes,
                    "epoch": self.server.epoch,
                    "maxInflight": self.server.max_inflight,
                    "calls": calls,
                }
            )
        with self.server.lock:
            self.server.calls[route] += 1
            mode = self.server.mode
            drop_cookies = self.server.drop_cookies
        if route == "/libgen/index.php":
            return self.reply(
                (
                    Path(__file__).parent / "fixtures" / "libgen-search.html"
                ).read_bytes(),
                content_type="text/html",
            )
        login = route == "/eapi/user/login"
        profile = route == "/eapi/user/profile"
        if (
            mode == "unauthorized"
            or (mode == "profile401" and profile)
            or (mode == "operation401" and not login and not profile)
        ):
            return self.reply({"success": 0, "error": "authentication rejected"}, 401)
        if mode == "login400" and login:
            return self.reply({"success": 0, "error": "login rejected"}, 400)
        if mode == "ambiguous400" and not login:
            return self.reply(
                {"success": 0, "error": "ambiguous operation failure"}, 400
            )
        if mode == "wall" and not login:
            return self.reply(b"<html>DiamWall block page</html>", 403, "text/html")
        if mode == "success0" and not login:
            return self.reply({"success": 0, "user": {"id": "populated-but-rejected"}})
        if mode == "timeout" and not login:
            time.sleep(35)  # Longer than httpx's 30s; MCP bridge budget is 15s.
        if mode == "slow":
            time.sleep(0.4)
        if login:
            fields = parse_qs(body.decode())
            if fields.get("email") != [
                "rehearsal-account@example.invalid"
            ] or fields.get("password") != ["rehearsal-password-canary"]:
                return self.reply({"success": 0}, 400)
            with self.server.lock:
                self.server.successes += 1
                cookie_key = f"{USER_KEY}-epoch-{self.server.epoch}"
            user = {} if drop_cookies else {"id": USER_ID, "remix_userkey": cookie_key}
            return self.reply(
                {"success": 1, "user": user},
                headers={"Set-Cookie": f"remix_userid={USER_ID}; Secure; HttpOnly"},
            )
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        if any(
            cookies.get(k) is None or cookies[k].value != v
            for k, v in {
                "remix_userid": USER_ID,
                "remix_userkey": f"{USER_KEY}-epoch-{self.server.epoch}",
            }.items()
        ):
            return self.reply({"success": 0, "error": "missing session"}, 401)
        book = {
            "id": 101,
            "hash": "hash101",
            "title": "Rehearsal book 101",
            "author": "Offline Author",
            "extension": "txt",
            "year": "2026",
            "language": "english",
            "filesize": 27,
            "description": "Details for rehearsal book 101",
        }
        if profile:
            return self.reply(
                {
                    "success": 1,
                    "user": {
                        "id": USER_ID,
                        "downloads_limit": 10,
                        "downloads_today": 3,
                        "isPremium": 0,
                    },
                }
            )
        if route == "/eapi/info/domains":
            return self.reply({"success": 1, "domains": []})
        if route == "/eapi/book/search":
            query = parse_qs(body.decode()).get("message", [""])[0]
            if query.startswith("slow-"):
                time.sleep(0.6)
            return self.reply(
                {"success": 1, "books": [{**book, "title": f"Rehearsal {query}"}]}
            )
        if route in {"/eapi/user/book/downloaded", "/eapi/book/recently"}:
            return self.reply({"success": 1, "books": [book]})
        if re.fullmatch(r"/eapi/book/101/hash101", route):
            return self.reply({"success": 1, "book": book})
        if route == "/eapi/book/101/hash101/file":
            return self.reply(
                {"success": 1, "file": {"downloadLink": "/files/101.txt"}}
            )
        if route == "/files/101.txt":
            return self.reply(
                b"Offline rehearsal book 101.\n",
                content_type="text/plain",
                headers={"Content-Disposition": 'attachment; filename="101.txt"'},
            )
        self.reply({"error": "unsupported fixture endpoint"}, 404)


if __name__ == "__main__":
    server = Fake(*sys.argv[1:])
    print(server.server_port, flush=True)

    def stop_at_eof():
        sys.stdin.buffer.read()
        server.shutdown()

    threading.Thread(target=stop_at_eof, daemon=True).start()
    try:
        server.serve_forever(poll_interval=0.05)
    finally:
        server.server_close()
