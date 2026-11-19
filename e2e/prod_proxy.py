"""Stand-in for the nginx container, for testing without Docker.

Serves client/dist/client/browser on :8080, falls back to index.html for Angular routes, and forwards /api/* to the
backend on :8000 with the /api prefix stripped. This is the same job client/nginx.conf does in the real deployment.
"""
import http.server
import pathlib
import urllib.request
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent / "client" / "dist" / "client" / "browser"
BACKEND = "http://127.0.0.1:8000"


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _proxy(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) if self.command in ("POST", "PUT", "DELETE") else None
        req = urllib.request.Request(BACKEND + self.path[len("/api"):], data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in ("host", "content-length"):
                req.add_header(k, v)
        try:
            resp = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            resp = e
        data = resp.read()
        self.send_response(resp.status if hasattr(resp, "status") else resp.code)
        for k, v in resp.headers.items():
            if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _static(self):
        path = (ROOT / self.path.split("?")[0].lstrip("/")).resolve()
        if not str(path).startswith(str(ROOT)) or not path.is_file():
            path = ROOT / "index.html"
        data = path.read_bytes()
        ctype = {".js": "text/javascript", ".css": "text/css", ".html": "text/html"}.get(path.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_any(self):
        self._proxy() if self.path.startswith("/api/") else self._static()

    do_GET = do_POST = do_DELETE = do_PUT = do_OPTIONS = handle_any


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
