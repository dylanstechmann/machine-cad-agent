"""Explicit units and bounded inputs, independent of a desktop CAD session."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    width_mm: float = Field(default=600.0, ge=200, le=2000)
    depth_mm: float = Field(default=400.0, ge=150, le=1500)
    height_mm: float = Field(default=360.0, ge=150, le=1500)
    frame_mm: float = Field(default=20.0, ge=10, le=60)
    tube_wall_mm: float = Field(default=2.0, ge=1, le=8)
    rail_diameter_mm: float = Field(default=12.0, ge=6, le=30)
    rail_spacing_mm: float = Field(default=160.0, ge=50, le=1000)
    rail_axis_above_frame_mm: float = Field(default=24.0, ge=10, le=100)
    support_width_mm: float = Field(default=28.0, ge=10, le=80)
    support_depth_mm: float = Field(default=30.0, ge=12, le=100)
    support_height_mm: float = Field(default=36.0, ge=20, le=150)
    carriage_width_mm: float = Field(default=100.0, ge=50, le=300)
    carriage_depth_mm: float = Field(default=200.0, ge=80, le=1200)
    plate_thickness_mm: float = Field(default=8.0, ge=3, le=25)
    bearing_length_mm: float = Field(default=40.0, ge=20, le=100)
    bearing_depth_mm: float = Field(default=30.0, ge=16, le=100)
    bearing_height_mm: float = Field(default=20.0, ge=12, le=80)
    radial_clearance_mm: float = Field(default=0.25, ge=0.05, le=1.0)
    minimum_clearance_mm: float = Field(default=2.0, ge=0.1, le=20)
    travel_mm: float = Field(default=360.0, ge=0, le=2000)
    motion_samples: int = Field(default=5, ge=3, le=21)

    @model_validator(mode="after")
    def check_layout(self):
        f = self.frame_mm
        if 2 * self.tube_wall_mm >= f:
            raise ValueError("tube_wall_mm must leave a hollow tube interior")
        if min(self.width_mm, self.depth_mm, self.height_mm) <= 3 * f:
            raise ValueError("frame members need a positive interior span")
        if self.rail_spacing_mm + self.support_depth_mm >= self.depth_mm - 2 * f:
            raise ValueError("rail supports must fit between the side frame members")
        if self.carriage_depth_mm < self.rail_spacing_mm + self.bearing_depth_mm:
            raise ValueError("carriage_depth_mm must cover both bearing blocks")
        if self.carriage_width_mm < self.bearing_length_mm:
            raise ValueError("carriage_width_mm must cover the bearing length")
        bore = self.rail_diameter_mm + 2 * self.radial_clearance_mm
        if bore + 4 >= min(self.bearing_height_mm, self.bearing_depth_mm):
            raise ValueError("bearing block must leave at least 2 mm around the bore")
        radius = self.rail_diameter_mm / 2 + 0.2
        z = self.rail_axis_above_frame_mm
        if z - radius < 2 or z + radius > self.support_height_mm - 2:
            raise ValueError("rail bore must fit inside the support with 2 mm margins")
        if self.support_depth_mm < 2 * radius + 4:
            raise ValueError("support_depth_mm must leave material around the bore")
        return self


def load_parameters(root: Path, patch: dict | None = None) -> Parameters:
    data = json.loads((root / "configs" / "m01.json").read_text(encoding="utf-8"))
    data.update(patch or {})
    return Parameters.model_validate(data)
