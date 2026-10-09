"""Engineering views with an explicit up direction and centered canvas."""

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import cadquery as cq
import cairosvg
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt


def render_view(shape: cq.Shape, direction: tuple, svg_path: Path) -> None:
    # CadQuery's SVG exporter chooses a camera X axis automatically. Align
    # the projected world Z axis with image up; top view uses world Y as up.
    axes = gp_Ax2(gp_Pnt(), gp_Dir(*direction))
    up = (0, 1, 0) if direction == (0, 0, 1) else (0, 0, 1)
    x, y = axes.XDirection(), axes.YDirection()
    dot_x = sum(a * b for a, b in zip(up, (x.X(), x.Y(), x.Z())))
    dot_y = sum(a * b for a, b in zip(up, (y.X(), y.Y(), y.Z())))
    angle = math.degrees(math.atan2(dot_x, dot_y))
    oriented = shape.rotate((0, 0, 0), direction, angle)
    svg = cq.exporters.getSVG(oriented, opts={
        "width": 1200, "height": None, "marginLeft": 45, "marginTop": 45,
        "projectionDir": direction, "showAxes": False, "showHidden": False,
        "strokeWidth": 0.8, "strokeColor": (34, 55, 75)})
    # Preserve geometry proportions while fitting and centering in 1200x850.
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    document = ET.fromstring(svg)
    document.set("viewBox", f"0 0 {document.get('width')} {document.get('height')}")
    document.set("width", "1200")
    document.set("height", "850")
    document.set("preserveAspectRatio", "xMidYMid meet")
    svg_path.write_text(ET.tostring(document, encoding="unicode"), encoding="utf-8")
    cairosvg.svg2png(url=str(svg_path), write_to=str(svg_path.with_suffix(".png")), background_color="white")
