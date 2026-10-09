"""M01 gantry layout: hollow stock tubes, round rails, bored blocks and a plate.

These are nominal geometry envelopes, not vendor-specific parts. All geometry
uses mm. Parts export at their local origin; the assembly supplies placements.
"""

from dataclasses import dataclass

import cadquery as cq

from .parameters import Parameters


@dataclass
class Component:
    name: str
    shape: cq.Shape
    placement: tuple[float, float, float]
    category: str
    description: str
    moving: bool = False
    color: tuple[float, float, float] = (0.45, 0.53, 0.61)

    def world(self, position: float = 0) -> cq.Shape:
        x, y, z = self.placement
        return self.shape.translate((x + (position if self.moving else 0), y, z))


def tube(length: float, f: float, wall: float, axis: str) -> cq.Shape:
    outer = {"x": (length, f, f), "y": (f, length, f), "z": (f, f, length)}[axis]
    inner = tuple(size + 2 if i == "xyz".index(axis) else size - 2 * wall
                  for i, size in enumerate(outer))
    return cq.Workplane("XY").box(*outer).cut(cq.Workplane("XY").box(*inner)).val()


def bored_block(x: float, y: float, z: float, diameter: float, bore_z: float = 0) -> cq.Shape:
    bore = cq.Workplane("YZ").center(0, bore_z).circle(diameter / 2).extrude(x + 2, both=True)
    return cq.Workplane("XY").box(x, y, z).cut(bore).val()


def generate(p: Parameters) -> list[Component]:
    parts = []
    f, w, d, h = p.frame_mm, p.width_mm, p.depth_mm, p.height_mm

    def add(name, shape, xyz, category, description, moving=False, color=(0.45, 0.53, 0.61)):
        parts.append(Component(name, shape, xyz, category, description, moving, color))

    for sx in (-1, 1):
        for sy in (-1, 1):
            add(f"post_{sx:+d}_{sy:+d}".replace("+", "p").replace("-", "m"),
                tube(h, f, p.tube_wall_mm, "z"), (sx * (w - f) / 2, sy * (d - f) / 2, h / 2),
                "stock", f"Nominal hollow square tube {f:g} x {f:g}, length {h:g} mm")
    for level, z in (("bottom", f / 2), ("top", h - f / 2)):
        for side, sign in (("left", -1), ("right", 1)):
            add(f"{level}_cross_{side}", tube(d - 2 * f, f, p.tube_wall_mm, "y"),
                (sign * (w - f) / 2, 0, z), "stock", f"Cross tube, length {d - 2*f:g} mm")
        for side, sign in (("front", -1), ("rear", 1)):
            add(f"{level}_long_{side}", tube(w - 2 * f, f, p.tube_wall_mm, "x"),
                (0, sign * (d - f) / 2, z), "stock", f"Long tube, length {w - 2*f:g} mm")

    rail_z = h + p.rail_axis_above_frame_mm
    for side, sy in (("front", -1), ("rear", 1)):
        y = sy * p.rail_spacing_mm / 2
        rail = cq.Workplane("YZ").circle(p.rail_diameter_mm / 2).extrude((w - f) / 2, both=True).val()
        add(f"rail_{side}", rail, (0, y, rail_z), "stock",
            f"Nominal round rail diameter {p.rail_diameter_mm:g}, length {w-f:g} mm",
            color=(0.70, 0.77, 0.82))
        for end, sx in (("left", -1), ("right", 1)):
            support = bored_block(p.support_width_mm, p.support_depth_mm, p.support_height_mm,
                                  p.rail_diameter_mm + 0.4,
                                  p.rail_axis_above_frame_mm - p.support_height_mm / 2)
            add(f"support_{side}_{end}", support,
                (sx * (w - f) / 2, y, h + p.support_height_mm / 2), "printable-study",
                "Bored rail support; attachment and clamping hardware not modeled",
                color=(0.13, 0.64, 0.61))
        bearing = bored_block(p.bearing_length_mm, p.bearing_depth_mm, p.bearing_height_mm,
                              p.rail_diameter_mm + 2 * p.radial_clearance_mm)
        add(f"bearing_{side}", bearing, (0, y, rail_z), "printable-study",
            "Sliding block envelope; bearing material and wear not validated", True,
            color=(0.95, 0.64, 0.20))

    hole_y = p.bearing_depth_mm / 2 - 4
    hole_x = p.bearing_length_mm / 2 - 6
    holes = [(x, sy * p.rail_spacing_mm / 2 + dy)
             for x in (-hole_x, hole_x) for sy in (-1, 1) for dy in (-hole_y, hole_y)]
    plate = (cq.Workplane("XY").box(p.carriage_width_mm, p.carriage_depth_mm, p.plate_thickness_mm)
             .faces(">Z").workplane().pushPoints(holes).hole(4.5).val())
    add("carriage_plate", plate, (0, 0, rail_z + (p.bearing_height_mm + p.plate_thickness_mm) / 2),
        "fabricated-study", "Plate with nominal 4.5 mm mounting holes; hardware not modeled", True,
        color=(0.16, 0.46, 0.77))
    return parts


def assembly(parts: list[Component], position: float = 0) -> cq.Assembly:
    result = cq.Assembly(name="M01_gantry_pilot")
    for part in parts:
        x, y, z = part.placement
        loc = cq.Location(cq.Vector(x + (position if part.moving else 0), y, z))
        result.add(part.shape, name=part.name, loc=loc, color=cq.Color(*part.color))
    return result
