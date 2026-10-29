"""Loopback-only teaching application. No query logs, external requests or writes."""

import argparse, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .engine import ROOT, load_catalog, recommend

CATALOG = load_catalog()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, body, kind="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get("Host") in [
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        ]

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {"error": "Loopback host required"})
        files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/style.css": ("style.css", "text/css; charset=utf-8"),
        }
        if self.path in files:
            name, kind = files[self.path]
            return self.send(200, (ROOT / "web" / name).read_bytes(), kind)
        if self.path == "/api/catalog":
            return self.send(
                200,
                {
                    "count": len(CATALOG),
                    "examples": [r for r in CATALOG if r["year"] == 2024][:8],
                },
            )
        return self.send(404, {"error": "Not found"})

    def do_POST(self):
        if not self.valid_host():
            return self.send(403, {"error": "Loopback host required"})
        origin = self.headers.get("Origin")
        allowed = [
            f"http://127.0.0.1:{self.server.server_port}",
            f"http://localhost:{self.server.server_port}",
        ]
        if origin and origin not in allowed:
            return self.send(403, {"error": "Same-origin requests only"})
        if self.path != "/api/recommend":
            return self.send(404, {"error": "Not found"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "Use application/json"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 8192:
                return self.send(413, {"error": "JSON body must be 1..8192 bytes"})
            body = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(body, dict) or set(body) - {
                "query",
                "limit",
                "before_year",
            }:
                raise ValueError("Use query, optional limit and before_year")
            result = recommend(
                body.get("query"),
                CATALOG,
                limit=body.get("limit", 5),
                before_year=body.get("before_year"),
            )
        except (ValueError, TypeError, UnicodeError) as error:
            return self.send(400, {"error": str(error)})
        return self.send(200, result)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=18341)
    a = p.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    server.daemon_threads = True
    print(
        f"Paper recommender: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
