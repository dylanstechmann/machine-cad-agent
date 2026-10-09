"""One interface for humans, CI and an agent's subprocess tools."""

import argparse
import contextlib
import json
import os
import sys
from pathlib import Path

from .pipeline import build, demo, get_build, inspect


def project_root() -> Path:
    root = Path(os.environ.get("MACHINE_CAD_ROOT", Path.cwd())).resolve()
    if not (root / "configs" / "pocket_pal.json").is_file():
        raise ValueError("Run from the project folder or set MACHINE_CAD_ROOT")
    return root


def compact(report: dict) -> dict:
    return {key: report[key] for key in ("build_id", "status", "artifact_directory", "fabrication_exports",
                                        "failures", "recipe", "sequence_frames", "path_sampling", "diagnostic_views", "source_sha256", "physical_readiness")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuildable Pocket Pal CAD and agent tools")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "check"):
        command = commands.add_parser(name)
        command.add_argument("--patch", default="{}", help="JSON object of parameter overrides")
        if name == "build":
            command.add_argument("--label", default="pocket-pal")
    commands.add_parser("demo")
    commands.add_parser("parameters")
    commands.add_parser("hardware")
    sim = commands.add_parser("sim-train",help="Train a supported-arm wrist reach experiment in MuJoCo")
    sim.add_argument("--steps",type=int,default=65536)
    sim.add_argument("--seed",type=int,default=7)
    sim.add_argument("--evaluation-episodes",type=int,default=24)
    sim_read = commands.add_parser("sim-inspect")
    sim_read.add_argument("--run-id")
    report_cmd = commands.add_parser("inspect")
    report_cmd.add_argument("--build-id")
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    commands.add_parser("mcp")
    args = parser.parse_args()
    try:
        root = project_root()
        # Keep dependency messages away from machine-readable stdout.
        with contextlib.redirect_stdout(sys.stderr):
            if args.command == "build":
                patch = json.loads(args.patch)
                if not isinstance(patch, dict):
                    raise ValueError("--patch must contain a JSON object")
                result = compact(build(root, patch, args.label))
            elif args.command == "check":
                patch = json.loads(args.patch)
                if not isinstance(patch, dict):
                    raise ValueError("--patch must contain a JSON object")
                result = inspect(root, patch)[4]
            elif args.command == "demo":
                result = demo(root)
            elif args.command == "parameters":
                from .parameters import Parameters, load_parameters
                result = {"values": load_parameters(root).model_dump(), "schema": Parameters.model_json_schema()}
            elif args.command == "hardware":
                from .hardware import hardware_reference,physical_readiness
                result = {"reference":hardware_reference(root),"physical_readiness":physical_readiness(root)}
            elif args.command == "sim-train":
                from .simulation import train_simulation
                result = train_simulation(root,args.steps,args.seed,args.evaluation_episodes)
            elif args.command == "sim-inspect":
                from .simulation import read_simulation
                result = read_simulation(root,args.run_id)[1]
            elif args.command == "inspect":
                result = get_build(root, args.build_id)[1]
            elif args.command == "serve":
                from .viewer import serve_viewer
                serve_viewer(root, args.host, args.port)
                return 0
            elif args.command == "mcp":
                from .mcp_server import main as mcp_main
                # The MCP transport owns stdout; do not redirect it.
                with contextlib.redirect_stdout(sys.__stdout__):
                    mcp_main()
                return 0
        print(json.dumps(result, allow_nan=False))
        return 1 if result.get("status") == "fail" else 0
    except (ValueError, FileNotFoundError) as error:
        print(json.dumps({"status": "error", "message": str(error)}))
        return 2
