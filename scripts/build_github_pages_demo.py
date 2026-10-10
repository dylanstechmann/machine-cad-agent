#!/usr/bin/env python3
"""Package a CAD build's repeated pose geometry as one compact animated GLB."""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GLB_MAGIC = b"glTF"
JSON_CHUNK = b"JSON"
BIN_CHUNK = b"BIN\0"
POSE_INTERVAL_SECONDS = 0.8


def read_glb_json(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12:
            raise ValueError(f"Invalid GLB header: {path}")
        magic, version, _ = struct.unpack("<4sII", header)
        if magic != GLB_MAGIC or version != 2:
            raise ValueError(f"Expected a glTF 2.0 binary model: {path}")
        chunk_header = stream.read(8)
        if len(chunk_header) != 8:
            raise ValueError(f"Missing JSON chunk: {path}")
        length, kind = struct.unpack("<I4s", chunk_header)
        if kind != JSON_CHUNK:
            raise ValueError(f"First GLB chunk is not JSON: {path}")
        return json.loads(stream.read(length))


def read_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError(f"Invalid GLB file: {path}")
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if magic != GLB_MAGIC or version != 2 or declared_length != len(raw):
        raise ValueError(f"Invalid GLB 2.0 container: {path}")
    offset = 12
    document = None
    binary = None
    while offset < len(raw):
        chunk_length, chunk_type = struct.unpack_from("<I4s", raw, offset)
        offset += 8
        chunk = raw[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == JSON_CHUNK:
            document = json.loads(chunk)
        elif chunk_type == BIN_CHUNK:
            binary = chunk
    if document is None or binary is None:
        raise ValueError(f"GLB must contain JSON and binary chunks: {path}")
    return document, binary


def pack_floats(values: list[float]) -> bytes:
    return struct.pack("<" + "f" * len(values), *values)


def finite_bounds(values: list[float], components: int) -> tuple[list[float], list[float]]:
    columns = [values[i::components] for i in range(components)]
    return [min(col) for col in columns], [max(col) for col in columns]


def node_map(document: dict[str, Any], path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for node in document.get("nodes", []):
        name = node.get("name")
        if not name or name in result:
            raise ValueError(f"Node names must be unique in {path}")
        result[name] = node
    return result


def mesh_axis_length(document: dict[str, Any], node: dict[str, Any], axis: int) -> float:
    mesh = document["meshes"][node["mesh"]]
    extents = []
    for primitive in mesh["primitives"]:
        accessor = document["accessors"][primitive["attributes"]["POSITION"]]
        extents.append(accessor["max"][axis] - accessor["min"][axis])
    return max(extents)


def make_animation_glb(build_dir: Path, sequence: dict[str, Any], parameters: dict[str, Any]) -> bytes:
    frames = sequence["frames"]
    if not frames:
        raise ValueError("Task sequence has no frames")
    pose_files = [build_dir / frame["glb"] for frame in frames]
    for pose in pose_files:
        if not pose.is_file():
            raise FileNotFoundError(pose)

    documents = [read_glb_json(pose) for pose in pose_files]
    base_path = pose_files[-1]
    base, binary = read_glb(base_path)
    buffer_length = base["buffers"][0]["byteLength"]
    if buffer_length > len(binary):
        raise ValueError("GLB buffer length exceeds its binary chunk")
    binary = binary[:buffer_length]
    base_nodes = node_map(base, base_path)
    frame_nodes = [node_map(doc, path) for doc, path in zip(documents, pose_files, strict=True)]
    base_indices = {node["name"]: index for index, node in enumerate(base["nodes"])}

    animated_scales: dict[str, list[list[float]]] = {}
    final_fill = max(float(frame.get("fill_ml", 0.0)) for frame in frames)
    shake = base_nodes.get("shake_volume_preview")
    if shake:
        shake_height = mesh_axis_length(base, shake, 2)
        if shake_height <= 0:
            raise ValueError("Shake preview geometry has no vertical extent")
        animated_scales["shake_volume_preview"] = [
            [1.0, 1.0, max(0.001, min(1.0, float(frame.get("fill_ml", 0.0)) / final_fill))]
            if final_fill > 0 else [1.0, 1.0, 0.001]
            for frame in frames
        ]

    carafe = base_nodes.get("carafe_water_preview")
    if carafe:
        radius = float(parameters.get("blender_internal_radius_mm", 38.0))
        water_available = float(parameters.get("water_available_ml", 0.0))
        base_height = mesh_axis_length(base, carafe, 2)
        if base_height <= 0 or radius <= 0:
            raise ValueError("Carafe water preview geometry is invalid")
        maximum_height = float(parameters.get("blender_internal_height_mm", 152.0))
        water_heights = [
            min(maximum_height, max(0.0, water_available - float(frame.get("water_ml", 0.0)))
                * 1000.0 / (math.pi * radius * radius))
            for frame in frames
        ]
        final_height = max(water_heights[-1], 1e-6)
        animated_scales["carafe_water_preview"] = [
            [1.0, 1.0, max(0.001, height / final_height)] for height in water_heights
        ]

    tracks: list[tuple[int, str, list[list[float]]]] = []
    for name, index in base_indices.items():
        base_node = base_nodes[name]
        for path, components, identity in (
            ("translation", 3, [0.0, 0.0, 0.0]),
            ("rotation", 4, [0.0, 0.0, 0.0, 1.0]),
            ("scale", 3, [1.0, 1.0, 1.0]),
        ):
            if name in animated_scales and path == "scale":
                values = animated_scales[name]
            else:
                default = base_node.get(path, identity)
                values = [
                    frame_nodes[frame_index].get(name, base_node).get(path, default)
                    for frame_index in range(len(frames))
                ]
            first = values[0]
            if any(any(abs(float(a) - float(b)) > 1e-6 for a, b in zip(value, first, strict=True))
                   for value in values[1:]):
                tracks.append((index, path, values))

    times = [index * POSE_INTERVAL_SECONDS for index in range(len(frames))]
    animation = {"name": "Pocket Pal task rehearsal", "samplers": [], "channels": []}
    addition = bytearray()
    buffer_views = base.setdefault("bufferViews", [])
    accessors = base.setdefault("accessors", [])

    def append_accessor(payload: bytes, count: int, value_type: str, *, minimum=None, maximum=None) -> int:
        while (buffer_length + len(addition)) % 4:
            addition.append(0)
        byte_offset = buffer_length + len(addition)
        buffer_view_index = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": byte_offset, "byteLength": len(payload)})
        addition.extend(payload)
        accessor = {
            "bufferView": buffer_view_index,
            "componentType": 5126,
            "count": count,
            "type": value_type,
        }
        if minimum is not None:
            accessor["min"] = minimum
        if maximum is not None:
            accessor["max"] = maximum
        accessors.append(accessor)
        return len(accessors) - 1

    input_accessor = append_accessor(
        pack_floats(times), len(times), "SCALAR", minimum=[times[0]], maximum=[times[-1]]
    )
    accessor_type = {3: "VEC3", 4: "VEC4"}
    for node_index, path, values in tracks:
        flattened = [float(component) for value in values for component in value]
        minimum, maximum = finite_bounds(flattened, len(values[0]))
        output_accessor = append_accessor(
            pack_floats(flattened), len(values), accessor_type[len(values[0])],
            minimum=minimum, maximum=maximum,
        )
        sampler_index = len(animation["samplers"])
        animation["samplers"].append({
            "input": input_accessor,
            "output": output_accessor,
            "interpolation": "STEP",
        })
        animation["channels"].append({
            "sampler": sampler_index,
            "target": {"node": node_index, "path": path},
        })

    base.setdefault("animations", []).append(animation)
    base["buffers"][0]["byteLength"] = buffer_length + len(addition)
    binary += bytes(addition)
    while len(binary) % 4:
        binary += b"\0"

    json_chunk = json.dumps(base, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    while len(json_chunk) % 4:
        json_chunk += b" "
    total_length = 12 + 8 + len(json_chunk) + 8 + len(binary)
    return b"".join((
        struct.pack("<4sII", GLB_MAGIC, 2, total_length),
        struct.pack("<I4s", len(json_chunk), JSON_CHUNK), json_chunk,
        struct.pack("<I4s", len(binary), BIN_CHUNK), binary,
    ))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-id", help="Use a specific build instead of builds/latest.json")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.build_id:
        build_id = args.build_id
    else:
        build_id = json.loads((root / "builds" / "latest.json").read_text())["build_id"]
    build_dir = root / "builds" / build_id
    if not build_dir.is_dir():
        raise FileNotFoundError(build_dir)

    sequence = json.loads((build_dir / "sequence.json").read_text())
    parameters = json.loads((build_dir / "parameters.json").read_text())
    report = json.loads((build_dir / "report.json").read_text())
    if report.get("status") != "pass":
        raise ValueError(f"Refusing to publish a failed CAD build: {build_id}")
    scene = make_animation_glb(build_dir, sequence, parameters)
    output = root / "docs" / "assets"
    output.mkdir(parents=True, exist_ok=True)
    (output / "pocket-pal-task.glb").write_bytes(scene)

    interval = POSE_INTERVAL_SECONDS
    recipe = dict(sequence["recipe"])
    recipe["cap_target_torque_nm"] = parameters["cap_target_torque_nm"]
    recipe["cap_stop_torque_nm"] = parameters["cap_stop_torque_nm"]
    task = {
        "build_id": build_id,
        "status": report.get("status", "unknown"),
        "scope": report.get("scope", "Digital CAD and kinematic task concept"),
        "source_sha256": report.get("source_sha256"),
        "path_sampling": report.get("path_sampling"),
        "physical_readiness": {
            "manufacturing_release": report.get("physical_readiness", {}).get("manufacturing_release", False),
            "hardware_match_status": report.get("physical_readiness", {}).get("hardware_match_status", "unknown"),
            "blocker_count": len(report.get("physical_readiness", {}).get("blockers", [])),
        },
        "pose_interval_seconds": interval,
        "duration_seconds": interval * (len(sequence["frames"]) - 1),
        "recipe": recipe,
        "frames": [
            {
                "label": frame.get("label", "Task pose"),
                "phase": frame.get("phase", ""),
                "dialogue": frame.get("dialogue", ""),
                "fill_ml": frame.get("fill_ml", 0.0),
                "headspace_ml": frame.get("headspace_ml", 0.0),
                "powder_scoops": frame.get("powder_scoops", 0),
                "water_ml": frame.get("water_ml", 0.0),
                "human_ready": bool(frame.get("human_ready", False)),
            }
            for frame in sequence["frames"]
        ],
    }
    (output / "task.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    isometric = build_dir / "views" / "isometric.png"
    if isometric.is_file():
        (output / "isometric.png").write_bytes(isometric.read_bytes())
    print(json.dumps({
        "build_id": build_id,
        "poses": len(sequence["frames"]),
        "animated_tracks": len(json.loads(scene[20:20 + struct.unpack_from("<I", scene, 12)[0]])["animations"][0]["channels"]),
        "glb_bytes": len(scene),
        "assets": str(output.relative_to(root)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
