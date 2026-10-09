"""Reference evidence remains distinct from nominal CAD and manufacturing approval."""

import json
from pathlib import Path


def hardware_reference(root: Path) -> dict:
    return json.loads((root/"configs"/"hardware_reference.json").read_text(encoding="utf-8"))


def physical_readiness(root: Path) -> dict:
    reference = hardware_reference(root)
    return {"manufacturing_release": False, "reference_profile": reference["profile_id"],
        "cad_export_purpose": "digital_design_studies",
        "hardware_match_status": reference["status"],
        "blockers": reference["missing_measurements"] + [
            "Purchased actuator selection, tested torque/speed/current and joint mechanics",
            "Printed-part tolerances, fasteners, bearings, structural loads and assembly development",
            "Grasp/fixture reaction forces, calibrated dosing, balance and complete task control"
        ]}
