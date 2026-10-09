"""Reproducible CAD, motion artifacts and a bounded digital export gate."""

import csv
import hashlib
import importlib.metadata
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import cadquery as cq
from .model import assembly, templates, pose_parts
from .parameters import load_parameters
from .rendering import render_view
from .sequence import make_sequence
from .validation import bounds, validate

VIEWS = {"isometric":(1,1.4,1),"front":(0,1,0),"top":(0,0,1),"side":(1,0,0),
         "walking":(1,1.4,.8),"scoop_transfer":(1,1.4,1)}
BUILD_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}-[a-f0-9]{12}$")


def source_digest(root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted((root/"src"/"machine_cad").glob("*.py"))
    paths += [root/"configs"/"pocket_pal.json",root/"pyproject.toml",root/"uv.lock",root/"Dockerfile"]
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_json(path: Path,data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def inspect(root: Path,patch: dict|None=None):
    p = load_parameters(root,patch)
    base = templates(p)
    frames = make_sequence(p)
    try:
        parts = pose_parts(base,p,frames[5])
    except ValueError:
        # Preserve numeric failure diagnostics even when no limb can be posed.
        parts = base
    report = validate(parts,p,base)
    report.update({"schema_version":2,"model":"Pocket_Pal","units":{"length":"mm","volume":"mL","torque":"N m"},
                   "parameters":p.model_dump(),"source_sha256":source_digest(root),
                   "dependencies":{n:importlib.metadata.version(n) for n in ("cadquery","mcp","CairoSVG")}})
    return p,parts,base,frames,report


def get_build(root: Path,build_id: str|None=None):
    if build_id is None:
        latest = root/"builds"/"latest.json"
        if not latest.is_file(): raise ValueError("No build yet. Run build_model or the build command first.")
        build_id = json.loads(latest.read_text(encoding="utf-8"))["build_id"]
    if not BUILD_ID.fullmatch(build_id): raise ValueError("Invalid build identifier")
    directory = (root/"builds"/build_id).resolve()
    if directory.parent!=(root/"builds").resolve(): raise ValueError("Build directory must remain inside this project")
    report_path = directory/"report.json"
    if not report_path.is_file(): raise ValueError("Build identifier does not exist")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["stale_source"] = report["source_sha256"]!=source_digest(root)
    return directory,report


def build(root: Path,patch: dict|None=None,label="pocket-pal"):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}",label):
        raise ValueError("Label must use 1-48 lowercase letters, digits, underscores or hyphens")
    p,parts,base,frames,report = inspect(root,patch)
    identity = {"parameters":p.model_dump(),"source":report["source_sha256"],"dependencies":report["dependencies"]}
    digest = hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:12]
    build_id = f"{label}-{digest}"
    directory = root/"builds"/build_id
    directory.mkdir(parents=True,exist_ok=True)
    report.update({"build_id":build_id,"created_at_utc":datetime.now(timezone.utc).isoformat(),
                   "artifact_directory":directory.relative_to(root).as_posix(),"stale_source":False})
    write_json(directory/"parameters.json",p.model_dump())
    assy = assembly(parts)
    shape = assy.toCompound()
    report["assembly_bounds"] = bounds(shape)
    views = directory/"views"
    poses = directory/"poses"
    views.mkdir(exist_ok=True)
    poses.mkdir(exist_ok=True)
    rendered = {}
    for frame,sample in zip(frames,report["motion_samples"]):
        if not all(v["reachable"] for v in (*sample["arms"].values(),*sample["legs"].values())):
            frame["glb"] = None
            continue
        posed = pose_parts(base,p,frame)
        name = f"{frame['index']:03d}-{frame['id']}.glb"
        assembly(posed).export(str(poses/name))
        frame["glb"] = "poses/"+name
        rendered[frame["id"]] = posed
    for name,direction in VIEWS.items():
        selected = rendered.get("walk_1",parts) if name=="walking" else rendered.get("scoop_1_tip",parts) if name=="scoop_transfer" else parts
        if name in ("walking","front"):
            selected = [v for v in selected if v.group!="stationary" and not v.group.startswith("object_") and v.category!="visualization"]
        render_view(assembly(selected).toCompound(),direction,views/f"{name}.svg")
    assy.export(str(directory/"assembly.glb"))
    write_json(directory/"sequence.json",{"model":"Pocket_Pal","mode":"discrete kinematic key poses; no hardware actuation",
        "recipe":report["recipe"],"frames":frames,"human_actions":["Press the blender power button","Drink the shake","Thank Pocket Pal"],
        "robot_reply":"You're welcome!"})
    report["timeline"] = [{key:f[key] for key in ("index","id","label","phase","dialogue","fill_ml","headspace_ml","glb")} for f in frames]
    physical = [v for v in parts if v.category!="visualization"]
    with (directory/"bom.csv").open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=["name","category","quantity","description"])
        writer.writeheader()
        writer.writerows({"name":v.name,"category":v.category,"quantity":1,"description":v.description} for v in physical)
    report["fabrication_exports"] = report["status"]=="pass"
    if report["fabrication_exports"]:
        export_dir = directory/"parts"
        export_dir.mkdir(exist_ok=True)
        assembly(physical).export(str(directory/"assembly.step"))
        for part in physical:
            cq.exporters.export(part.shape,str(export_dir/f"{part.name}.step"))
            if part.category in ("printable-study","fixture-study"):
                part.shape.exportStl(str(export_dir/f"{part.name}.stl"),tolerance=.05,angularTolerance=.1,relative=False)
    report["artifacts"] = [{"path":v.relative_to(root).as_posix(),"bytes":v.stat().st_size,
        "sha256":hashlib.sha256(v.read_bytes()).hexdigest()} for v in sorted(directory.rglob("*")) if v.is_file() and v.name!="report.json"]
    write_json(directory/"report.json",report)
    write_json(root/"builds"/"latest.json",{"build_id":build_id})
    return report


def demo(root: Path):
    baseline = build(root,label="baseline")
    broken = build(root,{"target_fill_ml":700},"broken-overfill")
    repaired = build(root,label="repaired")
    if [v["status"] for v in (baseline,broken,repaired)]!=["pass","fail","pass"]:
        raise RuntimeError("Demo did not produce pass/fail/pass. Inspect build reports.")
    evidence = {"scenario":"Deterministic overfill fault and correction; digital checks only.",
                "baseline":baseline["build_id"],"broken":broken["build_id"],"repaired":repaired["build_id"],
                "statuses":["pass","fail","pass"],"broken_failures":broken["failures"],
                "fabrication_gate_verified":not broken["fabrication_exports"]}
    write_json(root/"builds"/"demo.json",evidence)
    return evidence
