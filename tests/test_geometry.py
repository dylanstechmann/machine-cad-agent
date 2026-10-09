import math
import tempfile
import unittest
from pathlib import Path
import cadquery as cq
from pydantic import ValidationError
from machine_cad.cli import project_root
from machine_cad.parameters import load_parameters
from machine_cad.model import templates,pose_parts,scoop
from machine_cad.kinematics import rotate,tool_location,solve_arm,solve_leg,norm,sub
from machine_cad.sequence import make_sequence,recipe,tightening_decision
from machine_cad.pipeline import inspect,get_build


class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = project_root()
        cls.p,cls.parts,cls.base,cls.frames,cls.report = inspect(cls.root)

    def test_baseline_checks_and_single_solids(self):
        self.assertEqual(self.report["status"],"pass",self.report["failures"])
        self.assertEqual(len(self.report["parts"]),59)
        self.assertTrue(all(v["valid"] and v["solid_count"]==1 for v in self.report["parts"]))

    def test_measured_shell_and_cavity(self):
        shell = next(v for v in self.report["parts"] if v["name"]=="shell_back")
        self.assertEqual(shell["local_bounds"]["size_mm"],[190,75,210])
        cup = next(v for v in self.base if v.name=="blender_cup")
        void = cq.Workplane("XY").circle(38).extrude(145).translate((0,0,3)).val()
        self.assertAlmostEqual(cup.shape.intersect(void).Volume(),0,places=4)
        self.assertAlmostEqual(void.Volume()/1000,self.report["recipe"]["capacity_ml"],places=2)

    def test_three_and_two_scoop_recipes(self):
        a,b = recipe(self.p),recipe(load_parameters(self.root,{"scoop_count":2}))
        self.assertEqual((a["top_up_water_ml"],b["top_up_water_ml"]),(210,240))
        self.assertEqual((a["final_fill_ml"],b["final_fill_ml"]),(500,500))
        self.assertAlmostEqual(a["headspace_ml"],157.787,places=3)

    def test_all_arm_fk_and_leg_lengths(self):
        for frame in self.frames:
            for side,a in frame["arms"].items():
                solved = solve_arm(self.p,side,a["tcp_mm"],a["euler_deg"],frame["body_y_mm"])
                self.assertTrue(solved["reachable"],frame["id"])
                self.assertLess(solved["position_error_mm"],1e-6)
                leg = solve_leg(self.p,side,frame["feet"][side],frame["body_y_mm"])
                self.assertTrue(leg["reachable"])
                self.assertAlmostEqual(norm(sub(leg["knee_mm"],leg["hip_mm"])),90)
                self.assertAlmostEqual(norm(sub(leg["ankle_mm"],leg["knee_mm"])),90)
                self.assertGreaterEqual(leg["floor_clearance_mm"],0)

    def test_rotation_matches_geometry_and_scoop_bowl(self):
        frame = next(f for f in self.frames if f["id"]=="scoop_1_tip")
        obj = frame["objects"]["scoop"]
        r = rotate((0,65,0),obj["euler_deg"])
        transformed = cq.Vertex.makeVertex(0,65,0).located(tool_location(obj["position_mm"],obj["euler_deg"])).toTuple()
        expected = tuple(a+b for a,b in zip(obj["position_mm"],r))
        self.assertLess(norm(sub(transformed,expected)),1e-6)
        self.assertAlmostEqual(expected[0],110)
        self.assertAlmostEqual(expected[1],190)
        self.assertAlmostEqual(expected[2],388)
        # The bowl cavity is a hemisphere of exactly the requested nominal scoop volume.
        radius = (3*30*1000/(2*math.pi))**(1/3)
        self.assertAlmostEqual(2*math.pi*radius**3/3/1000,30)
        self.assertTrue(scoop(self.p).isValid())

    def test_cap_helix_and_gripper_attachment(self):
        for frame in self.frames:
            if "thread" in frame:
                t = frame["thread"]
                base = 306 if t["object"]=="jar_lid" else 359
                self.assertAlmostEqual(frame["objects"][t["object"]]["position_mm"][2]-base,t["axial_lift_mm"])
            for obj in frame["objects"].values():
                if obj["held_by"]:
                    self.assertEqual(obj["position_mm"],frame["arms"][obj["held_by"]]["tcp_mm"])

    def test_torque_feedback_policy(self):
        self.assertEqual(tightening_decision(self.p,.3,False),"continue")
        self.assertEqual(tightening_decision(self.p,.45,True),"stop_success")
        self.assertEqual(tightening_decision(self.p,.7,True),"stop_fault")
        self.assertEqual(tightening_decision(self.p,.1,False,2),"stop_fault")
        self.assertEqual(tightening_decision(self.p,float("nan"),False),"stop_fault")
        for torque,seated,axial in ((None,False,0),(".5",True,0),(.5,"false",0),(True,True,0),(.5,True,None)):
            self.assertEqual(tightening_decision(self.p,torque,seated,axial),"stop_fault")

    def test_unreachable_is_not_clamped(self):
        p = load_parameters(self.root,{"arm_upper_mm":50,"arm_lower_mm":50})
        self.assertFalse(solve_arm(p,"left",(110,125,403))["reachable"])
        with self.assertRaises(ValueError): pose_parts(self.base,p,next(f for f in self.frames if f["id"]=="scoop_1_carry"))

    def test_staggered_hinges_and_seated_caps(self):
        for frame_id in ("hello","scoop_1_tip","initial_water_pour","human_ready"):
            posed = {v.name:v for v in pose_parts(self.base,self.p,next(f for f in self.frames if f["id"]==frame_id))}
            for side in ("left","right"):
                for upper,lower in (("upper_arm_","forearm_"),("upper_leg_","lower_leg_")):
                    self.assertLess(posed[upper+side].world().intersect(posed[lower+side].world()).Volume(),1e-3)
        posed = {v.name:v for v in self.parts}
        for cap,vessel in (("jar_lid","protein_jar"),("blender_lid","blender_cup")):
            self.assertLess(posed[cap].world().intersect(posed[vessel].world()).Volume(),1e-3)
            self.assertAlmostEqual(posed[cap].world().distance(posed[vessel].world()),0,places=4)

    def test_reject_overfill_gripper_and_torque_limits(self):
        r = inspect(self.root,{"target_fill_ml":700,"gripper_max_opening_mm":80,"cap_target_torque_nm":.75})[4]
        self.assertEqual(r["status"],"fail")
        names = {v["check"] for v in r["failures"]}
        self.assertTrue({"recipe_headspace","gripper_travel","torque_window"}<=names)

    def test_human_handoff_and_open_preconditions(self):
        self.assertFalse(any(f["robot_actuates_blender"] for f in self.frames))
        self.assertTrue(self.frames[-1]["human_ready"])
        self.assertFalse(self.frames[-1]["blender_open"])
        self.assertEqual(self.frames[-1]["powder_scoops"],3)
        self.assertEqual(self.frames[-1]["fill_ml"],500)
        self.assertTrue(all(f["blender_open"] for f in self.frames if f.get("dispensing_ml")))
        self.assertTrue(all(f["jar_open"] for f in self.frames if f.get("scoop_event")))

    def test_invalid_parameters(self):
        for patch in ({"unknown":1},{"scoop_count":4},{"scoop_count":2.5},{"cap_target_torque_nm":float("inf")},{"body_width_mm":-1}):
            with self.assertRaises(ValidationError): load_parameters(self.root,patch)
        with self.assertRaises(ValueError): get_build(self.root,"../../outside")

    def test_step_roundtrip(self):
        part = next(v for v in self.base if v.name=="shell_back")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"shell.step"
            cq.exporters.export(part.shape,str(path))
            imported = cq.importers.importStep(str(path)).val()
            self.assertTrue(imported.isValid())
            self.assertAlmostEqual(imported.Volume(),part.shape.Volume(),places=2)
            self.assertAlmostEqual(imported.BoundingBox().xlen,190,places=4)
