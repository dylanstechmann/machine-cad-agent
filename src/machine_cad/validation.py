"""Bounded digital checks. Passing is not a physical machine qualification."""

import math
from .kinematics import norm, sub, solve_arm, solve_leg, rotate
from .model import pose_parts
from .sequence import make_sequence, recipe
from .collisions import CollisionChecker
from .trajectory import interpolate,subdivisions,attachment_errors,sampling_policy,MAX_INTERIOR_SAMPLES,angle_delta


def limb_state(p,frame):
    arms = {s:solve_arm(p,s,a["tcp_mm"],a["euler_deg"],frame["body_y_mm"]) for s,a in frame["arms"].items()}
    legs = {s:solve_leg(p,s,frame["feet"][s],frame["body_y_mm"]) for s in ("left","right")}
    return arms,legs


def validate_paths(base,p,frames,checker):
    segments,failures,diagnostics = [],[],[]
    required = sum(subdivisions(a,b)-1 for a,b in zip(frames,frames[1:]))
    sampled = 0
    for a,b in zip(frames,frames[1:]):
        count = subdivisions(a,b)
        segment = {"from":a["id"],"to":b["id"],"subdivisions":count,"interior_samples_required":count-1,"interior_samples_checked":0,
                   "max_tcp_gap_mm":0.0,"max_euler_gap_deg":0.0,"failures":[]}
        ownership = attachment_errors(a,b)
        if ownership: segment["failures"].append({"fraction":None,"attachment_errors":ownership})
        previous = a
        for i in range(1,count+1):
            if ownership: break  # Invalid ownership has no defined geometric interpolation.
            if i<count and sampled>=MAX_INTERIOR_SAMPLES: break
            t = i/count
            frame = interpolate(a,b,t)
            for side in ("left","right"):
                aa,bb = previous["arms"][side],frame["arms"][side]
                segment["max_tcp_gap_mm"] = max(segment["max_tcp_gap_mm"],norm(sub(aa["tcp_mm"],bb["tcp_mm"])))
                segment["max_euler_gap_deg"] = max(segment["max_euler_gap_deg"],*(abs(v) for v in angle_delta(aa["euler_deg"],bb["euler_deg"])))
            previous = frame
            if i==count: continue  # Endpoints are checked in the key-pose report.
            sampled += 1
            segment["interior_samples_checked"] += 1
            arms,legs = limb_state(p,frame)
            unreachable = [s+" arm" for s,v in arms.items() if not v["reachable"]]+[s+" leg" for s,v in legs.items() if not v["reachable"]]
            errors = [s for s,v in arms.items() if v["reachable"] and v["position_error_mm"]>1e-6]
            floor = [s for s,v in legs.items() if v["reachable"] and v["floor_clearance_mm"]<0]
            collisions = [] if unreachable else checker.check(
                pose_parts(base,p,frame,include_visualization=False),include_detailed_hands_and_toes=False)
            if unreachable or collisions or errors or floor:
                failure = {"fraction":round(t,8),"unreachable":unreachable,"collisions":collisions,
                           "fk_errors":errors,"floor_penetration":floor}
                segment["failures"].append(failure)
                if len(diagnostics)<4:
                    diagnostics.append({"frame":frame,"failure":failure})
        for name in ("max_tcp_gap_mm","max_euler_gap_deg"): segment[name] = round(segment[name],4)
        segment["complete"] = segment["interior_samples_checked"]==count-1
        segment["status"] = "incomplete" if not segment["complete"] else "fail" if segment["failures"] else "pass"
        segments.append(segment)
        if segment["failures"]:
            failures.append({"check":"sampled_path","message":"Intermediate motion or attachment check failed",
                "from":a["id"],"to":b["id"],"failed_samples":len(segment["failures"]),"first_failure":segment["failures"][0]})
    complete = sampled==required
    if not complete:
        failures.append({"check":"sampling_incomplete","message":"Sampling is incomplete or its budget was exhausted; exports are withheld",
                         "required_interior_samples":required,"checked_interior_samples":sampled})
    summary = {"status":"incomplete" if not complete else "fail" if failures else "pass",
        "segment_count":len(segments),"key_pose_count":len(frames),"required_interior_samples":required,
        "checked_interior_samples":sampled,"total_checked_poses":sampled+len(frames),
        "failed_segments":sum(bool(s["failures"]) for s in segments),"policy":sampling_policy(),
        "max_observed_tcp_gap_mm":max((s["max_tcp_gap_mm"] for s in segments),default=0),
        "max_observed_euler_gap_deg":max((s["max_euler_gap_deg"] for s in segments),default=0)}
    return summary,segments,failures,diagnostics


def bounds(shape):
    b = shape.BoundingBox()
    return {"min_mm":[round(b.xmin,4),round(b.ymin,4),round(b.zmin,4)],
            "max_mm":[round(b.xmax,4),round(b.ymax,4),round(b.zmax,4)],
            "size_mm":[round(b.xlen,4),round(b.ylen,4),round(b.zlen,4)]}


def validate(parts,p,base_parts):
    failures,checks = [],[]
    checker = CollisionChecker()
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
        arms,legs = limb_state(p,frame)
        reachable = all(v["reachable"] for v in (*arms.values(),*legs.values()))
        check("limb_reach",reachable,"A limb target is unreachable",pose=frame["id"])
        for side,a in frame["arms"].items():
            check("gripper_travel",a["opening_mm"]<=p.gripper_max_opening_mm,
                  "Required jaw opening exceeds gripper travel",pose=frame["id"],side=side)
            if arms[side]["reachable"]:
                check("arm_forward_kinematics",arms[side]["position_error_mm"]<1e-6,
                      "Forward kinematics does not reproduce the requested tool point",pose=frame["id"],side=side)
        for side,l in legs.items():
            if l["reachable"]:
                check("foot_floor",l["floor_clearance_mm"]>=0,"A foot penetrates the floor",pose=frame["id"],side=side)
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
            posed = pose_parts(base_parts,p,frame,include_visualization=False)
            held_contacts = {(obj["held_by"],"object_"+name) for name,obj in frame["objects"].items() if obj["held_by"]}
            collisions = checker.check(posed,permitted_hand_object_contacts=held_contacts)
            check("keypose_collisions",not collisions,"Robot or object intersects a checked body/station/object part",
                  pose=frame["id"],collisions=collisions)
        check("human_power_control",not frame["robot_actuates_blender"],"The robot must leave the power button to the human",pose=frame["id"])
        samples.append({"pose":frame["id"],"arms":arms,"legs":legs,"collisions":collisions})
    final = frames[-1]
    check("handoff",final["human_ready"] and not final["blender_open"] and final["powder_scoops"]==p.scoop_count,
          "The final state must contain the specified scoops, a closed cap and the human handoff")
    path_summary,segments,path_failures,diagnostics = validate_paths(base_parts,p,frames,checker)
    failures.extend(path_failures)
    return {"status":"fail" if failures else "pass","parts":measured,"checks":checks,"failures":failures,
            "motion_samples":samples,"recipe":plan,"sequence_frames":len(frames),
            "path_sampling":path_summary,"trajectory_segments":segments,"diagnostic_poses":diagnostics,
            "collision_stats":checker.stats(),
            "scope":"Solid/recipe/IK/FK/attachment/cap checks plus exact selected B-rep intersections at key poses and sampled intermediate poses. Key poses check digit and toe solids; sampled paths check main hand/arm/leg/foot envelopes. Digit contact with the object explicitly held by that hand is treated as intentional geometric grasp contact. Limbs versus body/station/objects; objects versus body/station/other objects; body versus worktop. Adjacent mounting contacts and internal robot self-collisions are excluded. Finite sampling does not certify continuous or all-pairs collision freedom, balance, grip forces, fluid flow or hardware torque.",
            "hardware_status":"Digital concept; no constructed robot or calibrated vendor mechanism."}
