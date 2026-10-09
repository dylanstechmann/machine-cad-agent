import math
import tempfile
import unittest
from pathlib import Path

import cadquery as cq
from pydantic import ValidationError

from machine_cad.cli import project_root
from machine_cad.model import generate
from machine_cad.parameters import load_parameters
from machine_cad.pipeline import build, get_build
from machine_cad.validation import bounds, validate


class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = project_root()
        cls.parameters = load_parameters(cls.root)
        cls.parts = generate(cls.parameters)
        cls.report = validate(cls.parts, cls.parameters)

    def test_baseline_geometry_and_measured_sliding_clearance(self):
        self.assertEqual(self.report["status"], "pass", self.report["failures"])
        self.assertEqual(len(self.parts), 21)
        self.assertTrue(all(p["valid"] and p["solid_count"] == 1 for p in self.report["parts"]))
        gaps = [g["clearance_mm"] for sample in self.report["motion_samples"]
                for g in sample["rail_clearances"] if g["parts"] == ["bearing_front", "rail_front"]]
        self.assertTrue(all(abs(gap - 0.25) < 1e-6 for gap in gaps), gaps)

    def test_actual_plate_dimensions_and_eight_through_holes(self):
        plate = next(p for p in self.parts if p.name == "carriage_plate")
        self.assertEqual(bounds(plate.shape)["size_mm"], [100.0, 200.0, 8.0])
        expected_volume = 100 * 200 * 8 - 8 * math.pi * 2.25**2 * 8
        self.assertAlmostEqual(plate.shape.Volume(), expected_volume, places=5)

    def test_excess_travel_reports_real_collision_with_support(self):
        p = load_parameters(self.root, {"travel_mm": 500.0})
        report = validate(generate(p), p)
        self.assertEqual(report["status"], "fail")
        collisions = [f for f in report["failures"] if f.get("overlap_mm3", 0) > 0]
        self.assertTrue(collisions)
        self.assertTrue(any("carriage_plate" in f["parts"] for f in collisions))

    def test_sparse_samples_cannot_skip_end_supports_or_leave_rails(self):
        p = load_parameters(self.root, {"travel_mm": 2000.0, "motion_samples": 3})
        report = validate(generate(p), p)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any(f["check"] == "travel_envelope" and f["maximum_mm"] == 448.0
                            for f in report["failures"]))

    def test_invalid_dimensions_are_rejected(self):
        for patch in ({"tube_wall_mm": 10.0}, {"width_mm": float("nan")},
                      {"width_mm": "600"}, {"unknown_dimension": 12}, {"motion_samples": True}):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                load_parameters(self.root, patch)

    def test_step_roundtrip_preserves_plate_volume_and_bounds(self):
        shape = next(p.shape for p in self.parts if p.name == "carriage_plate")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plate.step"
            cq.exporters.export(shape, str(path))
            restored = cq.importers.importStep(str(path)).val()
            self.assertTrue(restored.isValid())
            self.assertAlmostEqual(restored.Volume(), shape.Volume(), places=4)
            self.assertEqual(bounds(restored)["size_mm"], bounds(shape)["size_mm"])

    def test_failed_build_withholds_fabrication_files_but_keeps_pngs(self):
        report = build(self.root, {"travel_mm": 500.0}, "test-failed")
        directory, _ = get_build(self.root, report["build_id"])
        self.assertFalse(report["fabrication_exports"])
        self.assertFalse((directory / "assembly.step").exists())
        self.assertFalse((directory / "parts").exists())
        self.assertTrue((directory / "views" / "isometric.png").read_bytes().startswith(b"\x89PNG"))

    def test_build_paths_cannot_escape_project(self):
        with self.assertRaises(ValueError):
            get_build(self.root, "../../outside")
