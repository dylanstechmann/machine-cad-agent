"""Local, read-only artifact viewer. It never serves source, credentials or arbitrary paths."""

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .pipeline import get_build


def serve_viewer(root: Path, host: str, port: int):
    class Handler(BaseHTTPRequestHandler):
        def send_data(self, data: bytes, kind: str, status=200):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, data, status=200):
            self.send_data(json.dumps(data).encode(), "application/json", status)

        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            try:
                if path == "/":
                    self.send_data((root / "web" / "index.html").read_bytes(), "text/html; charset=utf-8")
                elif path == "/api/latest":
                    self.send_json(get_build(root)[1])
                elif path == "/api/builds":
                    reports = sorted((root / "builds").glob("*/report.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                    data = [json.loads(p.read_text(encoding="utf-8")) for p in reports[:50]]
                    self.send_json([{key: r[key] for key in ("build_id", "status", "created_at_utc")} for r in data])
                elif path.startswith("/api/build/"):
                    self.send_json(get_build(root, path.removeprefix("/api/build/"))[1])
                elif path.startswith("/artifacts/"):
                    pieces = path.removeprefix("/artifacts/").split("/", 1)
                    directory, report = get_build(root, pieces[0])
                    name = pieces[1] if len(pieces) == 2 else ""
                    allowed = {Path(a["path"]).relative_to(report["artifact_directory"]).as_posix()
                               for a in report["artifacts"]} | {"report.json"}
                    file = (directory / name).resolve()
                    if name not in allowed or not file.is_relative_to(directory) or not file.is_file():
                        raise ValueError("Artifact does not exist")
                    kind = "model/gltf-binary" if file.suffix == ".glb" else mimetypes.guess_type(file.name)[0]
                    self.send_data(file.read_bytes(), kind or "application/octet-stream")
                elif path.startswith("/vendor/"):
                    vendor = (root / "web" / "vendor").resolve()
                    file = (vendor / path.removeprefix("/vendor/")).resolve()
                    if not file.is_relative_to(vendor) or not file.is_file():
                        raise ValueError("Vendor asset does not exist")
                    self.send_data(file.read_bytes(), mimetypes.guess_type(file.name)[0] or "text/plain")
                else:
                    self.send_json({"error": "Not found"}, 404)
            except (ValueError, FileNotFoundError, KeyError):
                self.send_json({"error": "Build or artifact not found. Run the build command first."}, 404)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"CAD viewer listening on http://{host}:{port}", flush=True)
    server.serve_forever()
