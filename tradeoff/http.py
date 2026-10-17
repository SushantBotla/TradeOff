"""Loopback-only HTTP helpers for the hackathon deployment behind SSH."""

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

from .common import TradeOffError, canonical

MAX_BODY = 131072
_OPENER = build_opener(ProxyHandler({}))


def post_json(url, body, timeout=6, headers=None):
    request = Request(url, data=canonical(body), headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    try:
        with _OPENER.open(request, timeout=timeout) as response:
            data = response.read(MAX_BODY + 1)
            if len(data) > MAX_BODY:
                raise TradeOffError("Upstream response exceeds size limit", 502)
            return json.loads(data)
    except HTTPError as exc:
        code = exc.code
        exc.close()
        raise TradeOffError(f"Upstream request rejected (HTTP {code})", code) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise TradeOffError("Upstream service unavailable or invalid response", 503) from None


class Handler(BaseHTTPRequestHandler):
    server_version = "TradeOff"
    sys_version = ""

    def log_message(self, *args):
        pass  # Never log credentials, query strings, request bodies or model prompts.

    def send(self, status, body, content_type="application/json; charset=utf-8"):
        data = canonical(body) if not isinstance(body, bytes) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise TradeOffError("Invalid content length") from None
        if length <= 0 or length > MAX_BODY:
            raise TradeOffError("Invalid request size", 413)
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise TradeOffError("Content-Type must be application/json", 415)
        try:
            body = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            raise TradeOffError("Invalid JSON") from None
        if not isinstance(body, dict):
            raise TradeOffError("JSON object required")
        return body

    def dispatch(self):
        host = self.headers.get("Host", "")
        match = re.fullmatch(r"(?:127\.0\.0\.1|localhost):([1-9][0-9]{0,4})", host)
        if not match or int(match.group(1)) > 65535:
            raise TradeOffError("Loopback Host header required", 403)
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + host:
            raise TradeOffError("Cross-origin requests are not allowed", 403)
        self.route(urlsplit(self.path).path)

    def handle_request(self):
        self.connection.settimeout(15)
        try:
            self.dispatch()
        except TradeOffError as exc:
            self.send(exc.status, {"error": str(exc)})
        except Exception:
            self.send(500, {"error": "Internal service error; see the local verification tools"})

    do_GET = handle_request
    do_POST = handle_request


def serve(handler, port):
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    server.serve_forever()

