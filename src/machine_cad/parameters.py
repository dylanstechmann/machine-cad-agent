"""Explicit dimensions, recipe volumes, and nominal control limits."""

import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    body_width_mm: float = Field(default=190, ge=160, le=280)
    body_depth_mm: float = Field(default=75, ge=65, le=120)
    body_height_mm: float = Field(default=210, ge=190, le=300)
    shell_wall_mm: float = Field(default=3, ge=2, le=6)
    hip_height_mm: float = Field(default=180, ge=150, le=220)
    leg_upper_mm: float = Field(default=90, ge=60, le=140)
    leg_lower_mm: float = Field(default=90, ge=60, le=140)
    arm_upper_mm: float = Field(default=180, ge=50, le=230)
    arm_lower_mm: float = Field(default=180, ge=50, le=230)
    shoulder_span_mm: float = Field(default=220, ge=200, le=340)
    shoulder_forward_mm: float = Field(default=95, ge=45, le=100)
    shoulder_height_mm: float = Field(default=330, ge=290, le=420)
    tool_offset_mm: float = Field(default=75, ge=50, le=90)
    gripper_max_opening_mm: float = Field(default=130, ge=30, le=180)
    hand_palm_width_mm: float = Field(default=84, ge=68, le=100)
    hand_palm_depth_mm: float = Field(default=24, ge=18, le=32)
    hand_palm_length_mm: float = Field(default=46, ge=36, le=60)
    finger_phalanx_length_mm: float = Field(default=28, ge=18, le=40)
    toe_length_mm: float = Field(default=30, ge=20, le=40)
    bench_height_mm: float = Field(default=180, ge=150, le=210)
    blender_internal_radius_mm: float = Field(default=38, ge=30, le=50)
    blender_internal_height_mm: float = Field(default=145, ge=110, le=200)
    vessel_wall_mm: float = Field(default=3, ge=2, le=5)
    blender_base_height_mm: float = Field(default=35, ge=25, le=50)
    scoop_count: int = Field(default=3, ge=2, le=3)
    scoop_ml: float = Field(default=30, ge=15, le=45)
    initial_water_ml: float = Field(default=200, ge=50, le=800)
    target_fill_ml: float = Field(default=500, ge=150, le=1500)
    minimum_headspace_ml: float = Field(default=80, ge=30, le=300)
    water_available_ml: float = Field(default=600, ge=200, le=1000)
    cap_target_torque_nm: float = Field(default=.45, ge=.05, le=2)
    cap_stop_torque_nm: float = Field(default=.7, ge=.1, le=2)
    cap_seat_min_nm: float = Field(default=.2, ge=.05, le=1)
    cap_damage_limit_nm: float = Field(default=1, ge=.1, le=3)
    cap_reopen_limit_nm: float = Field(default=.8, ge=.1, le=3)
    jar_thread_pitch_mm: float = Field(default=3, ge=1, le=5)
    blender_thread_pitch_mm: float = Field(default=2, ge=1, le=4)
    cap_turns: float = Field(default=2, ge=1, le=3)

    @model_validator(mode="after")
    def base_layout(self):
        if self.hip_height_mm - 20 >= self.leg_upper_mm + self.leg_lower_mm:
            raise ValueError("Legs must reach the standing ankle with a bent knee")
        if self.shoulder_span_mm < self.body_width_mm + 24:
            raise ValueError("Shoulders need clearance outside the shell")
        if self.shoulder_forward_mm < self.body_depth_mm / 2 + 15:
            raise ValueError("Forward shoulder mounts must clear the front face")
        return self


def load_parameters(root: Path, patch: dict | None = None) -> Parameters:
    data = json.loads((root / "configs/pocket_pal.json").read_text(encoding="utf-8"))
    data.update(patch or {})
    return Parameters.model_validate(data)
