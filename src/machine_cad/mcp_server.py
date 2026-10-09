"""Project-local tools; fresh subprocess builds pick up the agent's source edits."""

import json
import os
import subprocess
import sys
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Image
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from .cli import project_root
from .pipeline import VIEWS, get_build

mcp = MCPServer("machine-cad-agent", version="0.1.0", instructions=(
    "Inspect parameters before changes. Build after editing code or parameters. Read numeric failures and PNG views. "
    "Passing means the stated digital checks passed. Pocket Pal has no physical hardware adapter. Fabrication exports require a fresh passing build."
))
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
BUILD_OUTPUTS = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)


def run_command(*args: str) -> dict:
    root = project_root()
    env = os.environ.copy()
    env["MACHINE_CAD_ROOT"] = str(root)
    env["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run([sys.executable, "-m", "machine_cad", *args], cwd=root,
                               env=env, capture_output=True, text=True, timeout=180)
    if completed.returncode not in (0, 1):
        raise ToolError((completed.stdout or completed.stderr)[-4000:])
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("CAD command did not return JSON: " + completed.stderr[-2000:]) from error


def fresh_build(build_id: str | None):
    try:
        directory, report = get_build(project_root(), build_id)
    except (ValueError, FileNotFoundError) as error:
        raise ToolError(str(error)) from error
    if report["stale_source"]:
        raise ToolError("Source changed since this build. Rebuild before using its outputs.")
    return directory, report


@mcp.tool(annotations=READ_ONLY)
def get_parameters() -> dict[str, Any]:
    """Read Pocket Pal defaults and the schema for overrides. Length mm, volume mL, torque N m."""
    return run_command("parameters")


@mcp.tool(annotations=BUILD_OUTPUTS)
def build_model(parameter_patch: dict[str, Any] | None = None, label: str = "pocket-pal") -> dict[str, Any]:
    """Generate Pocket Pal, check key poses and recipe bounds, render views, and gate exports.

    Overrides apply to this build only; edit configs/pocket_pal.json to persist a new baseline.
    Returns a build identifier, explicit failures and artifact directory.
    """
    return run_command("build", "--patch", json.dumps(parameter_patch or {}), "--label", label)


@mcp.tool(annotations=READ_ONLY)
def check_model(parameter_patch: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate a proposed robot revision without writing exports. Read failures and scope."""
    return run_command("check", "--patch", json.dumps(parameter_patch or {}))


@mcp.tool(annotations=READ_ONLY)
def inspect_model(build_id: str | None = None) -> dict[str, Any]:
    """Read a build's provenance, dimensions, failures, motion samples and artifact hashes.

    Omit build_id for the latest build. stale_source means rebuilding is required.
    """
    args = ["inspect"] + (["--build-id", build_id] if build_id else [])
    return run_command(*args)


@mcp.tool(annotations=READ_ONLY)
def measure_part(part_name: str, build_id: str | None = None) -> dict[str, Any]:
    """Read a named part's actual solid volume, bounds and placement from a fresh build."""
    _, report = fresh_build(build_id)
    for part in report["parts"]:
        if part["name"] == part_name:
            return {"build_id": report["build_id"], "units": "mm", **part}
    raise ToolError("Unknown part. Read inspect_model for the available names.")


@mcp.tool(annotations=READ_ONLY)
def render_views(build_id: str | None = None, view: str = "all") -> list[Image]:
    """Return native PNG images: all, isometric, front, top, side, walking, scoop_transfer."""
    directory, _ = fresh_build(build_id)
    if view != "all" and view not in VIEWS:
        raise ToolError("View must be all or one of: " + ", ".join(VIEWS))
    names = list(VIEWS) if view == "all" else [view]
    return [Image(path=directory / "views" / f"{name}.png") for name in names]


@mcp.tool(annotations=READ_ONLY)
def get_sequence(build_id: str | None = None, start_index: int = 0, max_frames: int = 12) -> dict[str, Any]:
    """Read a page of robot key poses, held objects, fill state, cap helix and handoff.

    Follow next_index for the next page. max_frames is 1-24. The complete plan
    is in sequence.json. This is a digital plan; it does not command hardware.
    """
    directory,report = fresh_build(build_id)
    plan = json.loads((directory/"sequence.json").read_text(encoding="utf-8"))
    frames = plan.pop("frames")
    if start_index<0 or start_index>=len(frames) or not 1<=max_frames<=24:
        raise ToolError("start_index must identify an existing pose; max_frames must be 1-24")
    end = min(len(frames),start_index+max_frames)
    return {"build_id":report["build_id"],**plan,"total_frames":len(frames),"start_index":start_index,
            "next_index":end if end<len(frames) else None,"frames":frames[start_index:end]}


@mcp.tool(annotations=READ_ONLY)
def export_files(build_id: str | None = None) -> dict[str, Any]:
    """List STEP/STL, BOM and report paths for a fresh passing build. Failed builds are refused."""
    _, report = fresh_build(build_id)
    if not report["fabrication_exports"]:
        raise ToolError("Geometry checks failed. Fix failures and rebuild before fabrication export.")
    return {"build_id": report["build_id"], "artifact_directory": report["artifact_directory"],
            "files": [item for item in report["artifacts"]
                      if item["path"].endswith((".step", ".stl", "bom.csv", "parameters.json"))]}


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
