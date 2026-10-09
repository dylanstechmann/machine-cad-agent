"""Bounded digital checks. Passing is not a physical machine qualification."""

import math
import cadquery as cq
from .kinematics import norm, sub, solve_arm, solve_leg, rotate
from .model import pose_parts
from .sequence import make_sequence, recipe


def bounds(shape):
    b = shape.BoundingBox()
    return {"min_mm":[round(b.xmin,4),round(b.ymin,4),round(b.zmin,4)],
            "max_mm":[round(b.xmax,4),round(b.ymax,4),round(b.zmax,4)],
            "size_mm":[round(b.xlen,4),round(b.ylen,4),round(b.zlen,4)]}


def validate(parts,p,base_parts):
    failures,checks = [],[]
    def check(name,okay,message,**detail):
        checks.append({"check":name,"passed":bool(okay),**detail})
        if not okay: failures.append({"check":name,"message":message,**detail})
    measured = []
    for part in parts:
        if part.category=="visualization": continue
        valid = part.shape.isValid()
        count = len(part.shape.Solids())
        measured.append({"name":part.name,"category":part.category,"description":part.description,
                         "valid":valid,"solid_count":count,"volume_mm3":round(part.shape.Volume(),3),
                         "local_bounds":bounds(part.shape),"world_bounds":bounds(part.world()),
                         "placement":part.loc.toTuple()})
        check("solid_validity",valid and count==1,"Each component must be one valid solid",part=part.name)
    plan = recipe(p)
    check("recipe_headspace",plan["headspace_ml"]>=p.minimum_headspace_ml,
          "The recipe exceeds the permitted fill or leaves too little headspace",headspace_ml=plan["headspace_ml"])
    check("recipe_target",p.initial_water_ml+p.scoop_count*p.scoop_ml<=p.target_fill_ml,
          "Initial water and powder already exceed the target fill")
    check("water_supply",plan["total_water_ml"]<=p.water_available_ml<=math.pi*38**2*152/1000,
          "The water supply must fit the carafe and cover both pours")
    check("torque_window",p.cap_seat_min_nm<=p.cap_target_torque_nm<p.cap_stop_torque_nm
          <min(p.cap_damage_limit_nm,p.cap_reopen_limit_nm),
          "Nominal target/stop torques must fit the seating, damage and reopening window")
    frames = make_sequence(p)
    samples = []
    for frame in frames:
        arms = {s:solve_arm(p,s,a["tcp_mm"],a["euler_deg"],frame["body_y_mm"]) for s,a in frame["arms"].items()}
        legs = {s:solve_leg(p,s,frame["feet"][s],frame["body_y_mm"]) for s in ("left","right")}
        reachable = all(v["reachable"] for v in (*arms.values(),*legs.values()))
        check("limb_reach",reachable,"A limb target is unreachable",pose=frame["id"])
        for side,a in frame["arms"].items():
            check("gripper_travel",a["opening_mm"]<=p.gripper_max_opening_mm,
                  "Required jaw opening exceeds gripper travel",pose=frame["id"],side=side)
            if arms[side]["reachable"]:
                check("arm_forward_kinematics",arms[side]["position_error_mm"]<1e-6,
                      "Forward kinematics does not reproduce the requested tool point",pose=frame["id"],side=side)
        for name,obj in frame["objects"].items():
            if obj["held_by"]:
                a = frame["arms"][obj["held_by"]]
                check("held_object_transform",norm(sub(obj["position_mm"],a["tcp_mm"]))<1e-7 and obj["euler_deg"]==a["euler_deg"],
                      "Held object does not follow its gripper transform",pose=frame["id"],object=name)
        if frame.get("dispensing_ml"):
            check("open_cup_before_pour",frame["blender_open"],"Pouring requires an open blender",pose=frame["id"])
        if frame.get("scoop_event"):
            check("open_jar_before_scooping",frame["jar_open"],"Scooping requires an open protein container",pose=frame["id"])
        if frame.get("scoop_event")=="dispense":
            obj = frame["objects"]["scoop"]
            bowl = tuple(x+y for x,y in zip(obj["position_mm"],rotate((0,65,0),obj["euler_deg"])))
            check("scoop_over_cup",math.hypot(bowl[0]-110,bowl[1]-190)<1e-6,
                  "The scoop bowl misses the blender opening",pose=frame["id"])
        if "thread" in frame:
            t = frame["thread"]
            pitch = p.jar_thread_pitch_mm if t["object"]=="jar_lid" else p.blender_thread_pitch_mm
            expected = t["turns"]*pitch
            if frame["phase"]=="close_blender": expected = (p.cap_turns-t["turns"])*pitch
            obj = frame["objects"][t["object"]]
            base_z = p.bench_height_mm+126 if t["object"]=="jar_lid" else p.bench_height_mm+p.blender_base_height_mm+p.vessel_wall_mm+p.blender_internal_height_mm-4
            axis_x = -110 if t["object"]=="jar_lid" else 110
            yaw = (-1 if frame["phase"]=="close_blender" else 1)*t["turns"]*360
            actual = norm(sub(obj["position_mm"],(axis_x,190,base_z+expected)))<1e-7 and norm(sub(obj["euler_deg"],(0,0,yaw)))<1e-7
            check("cap_helix",abs(t["axial_lift_mm"]-expected)<1e-7 and actual,
                  "Cap axial travel does not follow the nominal thread pitch",pose=frame["id"])
        collisions = []
        if reachable:
            posed = pose_parts(base_parts,p,frame)
            moving = [v for v in posed if v.group.startswith(("upper_","fore_","tool_","jaw_"))]
            obstacle = cq.Compound.makeCompound([v.world() for v in posed if v.name in ("shell_back","faceplate","worktop")])
            # Actual B-rep intersections at every listed pose; joint contacts and held-object contacts are excluded.
            compound = cq.Compound.makeCompound([v.world() for v in moving])
            volume = compound.intersect(obstacle).Volume()
            if volume>1e-3:
                for v in moving:
                    overlap = v.world().intersect(obstacle).Volume()
                    if overlap>1e-3: collisions.append({"part":v.name,"overlap_mm3":round(overlap,3)})
            check("keypose_arm_body_bench",not collisions,"Arm or gripper intersects the body or worktop",
                  pose=frame["id"],collisions=collisions)
            by_name = {v.name:v for v in posed}
            targeted = []
            for obj_name in ("carafe","scoop"):
                obj = frame["objects"][obj_name]
                if not obj["held_by"]: continue
                side = obj["held_by"]
                for tool_name in ("palm_"+side,"wrist_"+side):
                    overlap = by_name[tool_name].world().intersect(by_name[obj_name].world()).Volume()
                    if overlap>1e-3: targeted.append({"parts":[tool_name,obj_name],"overlap_mm3":round(overlap,3)})
                for vessel in ("protein_jar","blender_cup","blender_base"):
                    overlap = by_name[obj_name].world().intersect(by_name[vessel].world()).Volume()
                    if overlap>1e-3: targeted.append({"parts":[obj_name,vessel],"overlap_mm3":round(overlap,3)})
            check("keypose_tool_vessel",not targeted,"Held tool intersects its palm/wrist or a vessel wall",
                  pose=frame["id"],collisions=targeted)
        check("human_power_control",not frame["robot_actuates_blender"],"The robot must leave the power button to the human",pose=frame["id"])
        samples.append({"pose":frame["id"],"arms":arms,"legs":legs,"collisions":collisions})
    final = frames[-1]
    check("handoff",final["human_ready"] and not final["blender_open"] and final["powder_scoops"]==p.scoop_count,
          "The final state must contain the specified scoops, a closed cap and the human handoff")
    return {"status":"fail" if failures else "pass","parts":measured,"checks":checks,"failures":failures,
            "motion_samples":samples,"recipe":plan,"sequence_frames":len(frames),
            "scope":"Valid solids, recipe bounds, IK/FK, held transforms, nominal cap helix, arm/body/worktop intersections, and held scoop/carafe versus palm/wrist/vessel walls at listed key poses. Intermediate paths, all-pairs collisions, grip forces, balance, fluid flow and hardware torque are not qualified.",
            "hardware_status":"Digital concept; no constructed robot or calibrated vendor mechanism."}
