"""Deterministic geometric interpolation; task events stay at their key poses."""

import copy
import math
from .kinematics import norm,sub,rotate

TRANSLATION_STEP_MM = 20.0
ANGLE_STEP_DEG = 15.0
GRIPPER_STEP_MM = 5.0
MAX_INTERIOR_SAMPLES = 4096
TOOL_RADIUS_BOUND_MM = 150.0


def lerp(a,b,t):
    return [x+(y-x)*t for x,y in zip(a,b)]


def angle_delta(a,b,unwrapped=False):
    return [y-x if unwrapped else (y-x+180)%360-180 for x,y in zip(a,b)]


def bowl_center(arm):
    return [x+y for x,y in zip(arm["tcp_mm"],rotate((0,65,0),arm["euler_deg"]))]


def thread_side(a,b):
    if "thread" not in b: return None
    obj = b["thread"]["object"]
    owner = b["objects"][obj]["held_by"]
    return owner if owner and a["objects"][obj]["held_by"]==owner else None


def interpolate(a,b,t):
    """Ordinary Euler commands take nearest equivalent angles; threads keep winding.

    A pickup attaches at t=1, a release detaches at t=0. The other task events
    remain at A until B. A held scoop uses a linearly interpolated world bowl
    center, so tipping cannot swing the bowl away from the cup axis.
    """
    if not 0<=t<=1: raise ValueError("Interpolation fraction must be 0-1")
    if t==0: return copy.deepcopy(a)
    if t==1: return copy.deepcopy(b)
    frame = copy.deepcopy(a)
    for key in ("thread","dispensing_ml","source","destination","scoop_event","dialogue"):
        frame.pop(key,None)
    frame.update({"id":f"{a['id']}--{b['id']}@{t:.6f}","label":f"Between {a['label']} and {b['label']}",
                  "phase":b["phase"],"dialogue":"","human_ready":False,
                  "interval":{"from":a["id"],"to":b["id"],"fraction":t}})
    frame["body_y_mm"] = a["body_y_mm"]+(b["body_y_mm"]-a["body_y_mm"])*t
    for side in ("left","right"):
        frame["feet"][side] = lerp(a["feet"][side],b["feet"][side],t)
        aa,bb = a["arms"][side],b["arms"][side]
        delta = angle_delta(aa["euler_deg"],bb["euler_deg"],side==thread_side(a,b))
        angles = [x+d*t for x,d in zip(aa["euler_deg"],delta)]
        scooping = a["objects"]["scoop"]["held_by"]==b["objects"]["scoop"]["held_by"]==side
        if scooping:
            bowl = lerp(bowl_center(aa),bowl_center(bb),t)
            tcp = [x-y for x,y in zip(bowl,rotate((0,65,0),angles))]
        else: tcp = lerp(aa["tcp_mm"],bb["tcp_mm"],t)
        frame["arms"][side] = {"tcp_mm":tcp,"euler_deg":angles,
            "opening_mm":aa["opening_mm"]+(bb["opening_mm"]-aa["opening_mm"])*t}
    for name,obj in frame["objects"].items():
        before,after = a["objects"][name],b["objects"][name]
        owner = before["held_by"]
        if owner and owner==after["held_by"]:
            arm = frame["arms"][owner]
            obj.update(position_mm=arm["tcp_mm"].copy(),euler_deg=arm["euler_deg"].copy())
        elif owner!=after["held_by"]:
            if owner and after["held_by"]:
                raise ValueError("Changing hands requires explicit release and pickup poses")
            obj["held_by"] = None
    return frame


def subdivisions(a,b):
    """Subdivide endpoint translation plus a conservative tool rotation allowance.

    This does not bound IK link sweeps near singularities or certify continuous
    collision freedom. Every resulting sample is independently solved and checked.
    """
    travel,rotation,jaw = abs(b["body_y_mm"]-a["body_y_mm"]),0.0,0.0
    for side in ("left","right"):
        aa,bb = a["arms"][side],b["arms"][side]
        delta = angle_delta(aa["euler_deg"],bb["euler_deg"],side==thread_side(a,b))
        rotation = max(rotation,max(abs(d) for d in delta))
        jaw = max(jaw,abs(bb["opening_mm"]-aa["opening_mm"]))
        scooping = a["objects"]["scoop"]["held_by"]==b["objects"]["scoop"]["held_by"]==side
        start,end = (bowl_center(aa),bowl_center(bb)) if scooping else (aa["tcp_mm"],bb["tcp_mm"])
        allowance = norm(sub(end,start))+TOOL_RADIUS_BOUND_MM*sum(abs(math.radians(d)) for d in delta)
        travel = max(travel,allowance,norm(sub(b["feet"][side],a["feet"][side])))
    return max(4,math.ceil(travel/TRANSLATION_STEP_MM),math.ceil(rotation/ANGLE_STEP_DEG),math.ceil(jaw/GRIPPER_STEP_MM))


def attachment_errors(a,b):
    failures = []
    for name,before in a["objects"].items():
        after = b["objects"][name]
        if before["held_by"]!=after["held_by"] and before["held_by"] and after["held_by"]:
            failures.append({"object":name,"message":"Direct handoff requires explicit release/pickup"})
        if before["held_by"] is None or after["held_by"] is None:
            if norm(sub(before["position_mm"],after["position_mm"]))>1e-6 or any(abs(d)>1e-6 for d in angle_delta(before["euler_deg"],after["euler_deg"])):
                failures.append({"object":name,"message":"An unheld object changes position or orientation"})
    return failures


def sampling_policy():
    return {"translation_allowance_step_mm":TRANSLATION_STEP_MM,"angular_step_deg":ANGLE_STEP_DEG,
        "jaw_step_mm":GRIPPER_STEP_MM,
        "minimum_subdivisions":4,"maximum_interior_samples":MAX_INTERIOR_SAMPLES,
        "tool_rotation_radius_allowance_mm":TOOL_RADIUS_BOUND_MM,
        "detailed_digit_and_toe_collisions":"Checked at task key poses; intermediate samples check the main hand/arm/leg/foot envelopes",
        "interpolation":"Cartesian tool/foot/body interpolation; scoop world-bowl interpolation; nearest-equivalent ordinary Euler commands; unwrapped thread yaw",
        "events":"Pickup at destination; release at source; recipe and other task events only at key poses",
        "limit":"Finite samples only; IK link sweeps and continuous collision freedom are not certified"}
