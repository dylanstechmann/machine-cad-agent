"""Build artifacts with input/source provenance and a gate on fabrication exports."""

import csv
import hashlib
import importlib.metadata
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import cadquery as cq

from .model import assembly, generate
from .parameters import load_parameters
from .rendering import render_view
from .validation import bounds, validate

VIEWS = {"isometric": (1, -1.4, 1), "front": (0, -1, 0), "top": (0, 0, 1),
         "side": (1, 0, 0), "motion_left": (1, -1.4, 1), "motion_right": (1, -1.4, 1)}
BUILD_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}-[a-f0-9]{12}$")


def source_digest(root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted((root / "src" / "machine_cad").glob("*.py"))
    paths += [root / "configs" / "m01.json", root / "pyproject.toml", root / "uv.lock", root / "Dockerfile"]
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def inspect(root: Path, patch: dict | None = None) -> tuple:
    p = load_parameters(root, patch)
    parts = generate(p)
    report = validate(parts, p)
    report.update({"schema_version": 1, "model": "M01_gantry_pilot", "units": "mm",
                   "parameters": p.model_dump(), "source_sha256": source_digest(root),
                   "dependencies": {name: importlib.metadata.version(name)
                                    for name in ("cadquery", "mcp", "CairoSVG")}})
    return p, parts, report


def get_build(root: Path, build_id: str | None = None) -> tuple[Path, dict]:
    if build_id is None:
        latest = root / "builds" / "latest.json"
        if not latest.is_file():
            raise ValueError("No build yet. Run build_model or the build command first.")
        build_id = json.loads(latest.read_text(encoding="utf-8"))["build_id"]
    if not BUILD_ID.fullmatch(build_id):
        raise ValueError("Invalid build identifier")
    directory = (root / "builds" / build_id).resolve()
    if directory.parent != (root / "builds").resolve():
        raise ValueError("Build directory must remain inside this project")
    report_path = directory / "report.json"
    if not report_path.is_file():
        raise ValueError("Build identifier does not exist")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["stale_source"] = report["source_sha256"] != source_digest(root)
    return directory, report


def build(root: Path, patch: dict | None = None, label: str = "m01") -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", label):
        raise ValueError("Label must use 1-48 lowercase letters, digits, underscores or hyphens")
    p, parts, report = inspect(root, patch)
    identity = {"parameters": p.model_dump(), "source": report["source_sha256"],
                "dependencies": report["dependencies"]}
    short_hash = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:12]
    build_id = f"{label}-{short_hash}"
    directory = root / "builds" / build_id
    directory.mkdir(parents=True, exist_ok=True)
    report.update({"build_id": build_id, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                   "artifact_directory": directory.relative_to(root).as_posix(), "stale_source": False})
    write_json(directory / "parameters.json", p.model_dump())
    assy = assembly(parts)
    shape = assy.toCompound()
    report["assembly_bounds"] = bounds(shape)
    views = directory / "views"
    views.mkdir(exist_ok=True)
    for name, direction in VIEWS.items():
        svg_path = views / f"{name}.svg"
        position = -p.travel_mm / 2 if name == "motion_left" else p.travel_mm / 2 if name == "motion_right" else 0
        view_shape = assembly(parts, position).toCompound() if position else shape
        render_view(view_shape, direction, svg_path)
    # GLB is a visual preview, available even when the fabrication gate fails.
    assy.export(str(directory / "assembly.glb"))
    with (directory / "bom.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["name", "category", "quantity", "description"])
        writer.writeheader()
        writer.writerows({"name": part.name, "category": part.category, "quantity": 1,
                         "description": part.description} for part in parts)
    report["fabrication_exports"] = report["status"] == "pass"
    if report["fabrication_exports"]:
        export_dir = directory / "parts"
        export_dir.mkdir(exist_ok=True)
        assy.export(str(directory / "assembly.step"))
        for part in parts:
            cq.exporters.export(part.shape, str(export_dir / f"{part.name}.step"))
            if part.category == "printable-study":
                part.shape.exportStl(str(export_dir / f"{part.name}.stl"),
                                     tolerance=0.05, angularTolerance=0.1, relative=False)
    artifacts = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "report.json":
            artifacts.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size,
                              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    report["artifacts"] = artifacts
    write_json(directory / "report.json", report)
    write_json(root / "builds" / "latest.json", {"build_id": build_id})
    return report


def demo(root: Path) -> dict:
    baseline = build(root, label="baseline")
    invalid_travel = baseline["suggested_max_travel_mm"] + 52
    broken = build(root, {"travel_mm": invalid_travel}, "broken-clearance")
    repaired = build(root, {"travel_mm": baseline["parameters"]["travel_mm"]}, "repaired")
    if baseline["status"] != "pass" or broken["status"] != "fail" or repaired["status"] != "pass":
        raise RuntimeError("Demo did not produce the required pass/fail/pass sequence")
    evidence = {"scenario": "Deterministic travel fault and correction; no autonomous LLM performance claim.",
                "baseline": baseline["build_id"], "broken": broken["build_id"],
                "repaired": repaired["build_id"], "statuses": ["pass", "fail", "pass"],
                "broken_failures": broken["failures"], "fabrication_gate_verified": not broken["fabrication_exports"]}
    write_json(root / "builds" / "demo.json", evidence)
    return evidence
