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
                elif path == "/simulation":
                    self.send_data((root/"web"/"simulation.html").read_bytes(),"text/html; charset=utf-8")
                elif path == "/api/hardware":
                    from .hardware import hardware_reference,physical_readiness
                    self.send_json({"reference":hardware_reference(root),"physical_readiness":physical_readiness(root)})
                elif path == "/api/simulation/latest":
                    from .simulation import read_simulation
                    self.send_json(read_simulation(root)[1])
                elif path == "/api/simulation/runs":
                    from .simulation import read_simulation
                    paths = sorted((root/"builds"/"simulation").glob("*/report.json"),key=lambda p:p.stat().st_mtime,reverse=True)
                    reports = [read_simulation(root,p.parent.name)[1] for p in paths[:50]]
                    self.send_json([{k:r[k] for k in ("run_id","status","stale_source","actual_training_steps","training_seed")} for r in reports])
                elif path.startswith("/api/simulation/"):
                    from .simulation import read_simulation
                    self.send_json(read_simulation(root,path.removeprefix("/api/simulation/"))[1])
                elif path.startswith("/simulation-artifacts/"):
                    from .simulation import read_simulation,simulation_artifact
                    pieces = path.removeprefix("/simulation-artifacts/").split("/",1)
                    directory,report = read_simulation(root,pieces[0])
                    name = pieces[1] if len(pieces)==2 else ""
                    allowed = {a["name"] for a in report["artifacts"]} | {"report.json"}
                    file = (directory/name).resolve()
                    if name not in allowed or not file.is_relative_to(directory) or not file.is_file():
                        raise ValueError("Simulation artifact does not exist")
                    if name!="report.json": file,_ = simulation_artifact(root,pieces[0],name)
                    self.send_data(file.read_bytes(),mimetypes.guess_type(file.name)[0] or "application/octet-stream")
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
                    if file.suffix.lower() in (".step",".stl") and (report["stale_source"] or not report["fabrication_exports"]):
                        raise ValueError("Fabrication exports require a fresh passing report")
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
