"""Manipulation storyboard with held objects, helical cap motion and recipe state."""

import copy
import math
from numbers import Real
from .kinematics import rotate


def recipe(p):
    capacity = math.pi*p.blender_internal_radius_mm**2*p.blender_internal_height_mm/1000
    powder = p.scoop_count*p.scoop_ml
    top_up = max(0,p.target_fill_ml-p.initial_water_ml-powder)
    final = p.initial_water_ml+powder+top_up
    return {"capacity_ml":round(capacity,3),"initial_water_ml":p.initial_water_ml,
            "scoop_count":p.scoop_count,"scoop_capacity_ml":p.scoop_ml,
            "powder_displacement_bound_ml":powder,"top_up_water_ml":top_up,
            "total_water_ml":p.initial_water_ml+top_up,"final_fill_ml":final,
            "headspace_ml":round(capacity-final,3),"minimum_headspace_ml":p.minimum_headspace_ml,
            "calibration_status":"nominal volume and torque inputs; no hardware measurements"}


def tightening_decision(p, measured_torque_nm, seated, axial_error_mm=0):
    """Pure feedback policy for a future adapter; this never drives hardware."""
    if type(seated) is not bool:
        return "stop_fault"
    if any(isinstance(v,bool) or not isinstance(v,Real) or not math.isfinite(v)
           for v in (measured_torque_nm,axial_error_mm)) or measured_torque_nm < 0:
        return "stop_fault"
    if abs(axial_error_mm)>1 or measured_torque_nm>=p.cap_stop_torque_nm:
        return "stop_fault"
    if seated and measured_torque_nm>=p.cap_target_torque_nm:
        return "stop_success"
    return "continue"


def make_sequence(p):
    h = p.bench_height_mm
    rim = h+p.blender_base_height_mm+p.vessel_wall_mm+p.blender_internal_height_mm
    cap_diameter = 2*(p.blender_internal_radius_mm+p.vessel_wall_mm+2)
    jar_cap_z,blender_cap_z = h+126,rim-4
    scoop_rest = (-230,290,h+55)
    plan = recipe(p)
    state = {
        "body_y_mm":0,"feet":{"left":[-55,0,20],"right":[55,0,20]},
        "arms":{"left":{"tcp_mm":[-160,85,255],"euler_deg":[0,0,0],"opening_mm":125},
                "right":{"tcp_mm":[160,85,255],"euler_deg":[0,0,0],"opening_mm":125}},
        "objects":{"jar_lid":{"position_mm":[-110,190,jar_cap_z],"euler_deg":[0,0,0],"held_by":None},
                   "blender_lid":{"position_mm":[110,190,blender_cap_z],"euler_deg":[0,0,0],"held_by":None},
                   "carafe":{"position_mm":[230,150,h+120],"euler_deg":[0,0,0],"held_by":None},
                   "scoop":{"position_mm":list(scoop_rest),"euler_deg":[0,0,0],"held_by":None}},
        "water_ml":0.0,"powder_scoops":0,"jar_open":False,"blender_open":False,
        "human_ready":False,"robot_actuates_blender":False,"planned_torque_nm":0.0,
    }
    frames = []

    def emit(name,label,phase,dialogue="",**extra):
        frame = copy.deepcopy(state)
        frame.update({"id":name,"label":label,"phase":phase,"dialogue":dialogue,**extra})
        frame["index"] = len(frames)
        frame["fill_ml"] = frame["water_ml"]+frame["powder_scoops"]*p.scoop_ml
        frame["headspace_ml"] = plan["capacity_ml"]-frame["fill_ml"]
        frames.append(frame)

    def arm(side,tcp,angles=(0,0,0),opening=125,held=None):
        state["arms"][side] = {"tcp_mm":list(tcp),"euler_deg":list(angles),"opening_mm":opening}
        if held:
            state["objects"][held] = {"position_mm":list(tcp),"euler_deg":list(angles),"held_by":side}

    def rest(side):
        arm(side,((-160 if side=="left" else 160),85,255))

    clear_z = max(rim,h+130)+85

    def approach(side,tcp,prefix,phase):
        outward = -230 if side=="left" else 230
        arm(side,(outward,85,255))
        emit(prefix+"_outward","Move the empty hand clear of the vessels",phase)
        arm(side,(outward,85,clear_z))
        emit(prefix+"_raise","Raise the empty hand above the station",phase)
        arm(side,(outward,190,clear_z))
        emit(prefix+"_via","Move forward before crossing toward the grip",phase)
        arm(side,(tcp[0],tcp[1],clear_z))
        emit(prefix+"_above","Approach the grip from above",phase)

    def withdraw(side,prefix,phase):
        current = state["arms"][side]["tcp_mm"]
        outward = -230 if side=="left" else 230
        arm(side,(current[0],current[1],clear_z))
        emit(prefix+"_release_lift","Release and lift the empty hand clear",phase)
        if abs(current[0]-outward)>1e-7:
            arm(side,(outward,current[1],clear_z))
            emit(prefix+"_retreat_outward","Move outward before withdrawing toward the body",phase)
        arm(side,(outward,85,clear_z))
        emit(prefix+"_retreat_high","Withdraw above the station",phase)
        arm(side,(outward,85,255))
        emit(prefix+"_lower","Lower the empty hand outside the vessels",phase)
        rest(side)
        emit(prefix+"_rest","Return the hand to rest",phase)

    for i,(body,ly,lz,ry,rz) in enumerate(((-80,-80,20,-80,20),(-50,-80,20,-15,50),
                                         (-25,-80,20,0,20),(0,35,45,0,20),(0,0,20,0,20))):
        state["body_y_mm"] = body
        state["feet"] = {"left":[-55,ly,lz],"right":[55,ry,rz]}
        for side in ("left","right"):
            arm(side,((-160 if side=="left" else 160),85+body,255))
        emit(f"walk_{i}","Walk to the preparation station","walking")
    emit("hello","Hello, I'm Pocket Pal","greeting","Hello! I'll prepare your protein shake.")

    approach("left",(-110,190,jar_cap_z),"jar_approach","open_jar")
    arm("left",(-110,190,jar_cap_z),opening=120,held="jar_lid")
    emit("jar_grasp","Grip the protein container cap","open_jar")
    for fraction in (.125,.25,.375,.5,.625,.75,.875,1):
        turns = p.cap_turns*fraction
        arm("left",(-110,190,jar_cap_z+turns*p.jar_thread_pitch_mm),(0,0,turns*360),120,"jar_lid")
        emit(f"jar_turn_{fraction}","Unscrew the protein container","open_jar",
             thread={"object":"jar_lid","turns":turns,"axial_lift_mm":turns*p.jar_thread_pitch_mm})
    state["jar_open"] = True
    arm("left",(-110,190,h+210),opening=120,held="jar_lid")
    emit("jar_lift","Lift the protein cap clear","open_jar")
    arm("left",(-230,190,h+210),opening=120,held="jar_lid")
    emit("jar_carry_outward","Move the cap outward before approaching its stand","open_jar")
    arm("left",(-230,105,h+210),opening=120,held="jar_lid")
    emit("jar_carry","Carry the protein cap above its parking pad","open_jar")
    arm("left",(-230,105,h+40),opening=120,held="jar_lid")
    emit("jar_park","Park the protein cap","open_jar")
    state["objects"]["jar_lid"]["held_by"] = None
    withdraw("left","jar","open_jar")

    approach("right",(110,190,blender_cap_z),"blender_approach","open_blender")
    arm("right",(110,190,blender_cap_z),opening=cap_diameter,held="blender_lid")
    emit("blender_grasp","Grip the portable blender cap","open_blender")
    for fraction in (.125,.25,.375,.5,.625,.75,.875,1):
        turns = p.cap_turns*fraction
        arm("right",(110,190,blender_cap_z+turns*p.blender_thread_pitch_mm),
            (0,0,turns*360),cap_diameter,"blender_lid")
        emit(f"blender_open_{fraction}","Unscrew the blender cap","open_blender",
             thread={"object":"blender_lid","turns":turns,"axial_lift_mm":turns*p.blender_thread_pitch_mm})
    state["blender_open"] = True
    arm("right",(110,190,rim+65),opening=cap_diameter,held="blender_lid")
    emit("blender_lift","Lift the blender cap clear","open_blender")
    arm("right",(250,285,rim+65),opening=cap_diameter,held="blender_lid")
    emit("blender_carry","Carry the blender cap above its parking pad","open_blender")
    arm("right",(250,285,h+35),opening=cap_diameter,held="blender_lid")
    emit("blender_park","Park the blender cap","open_blender")
    state["objects"]["blender_lid"]["held_by"] = None
    withdraw("right","blender","open_blender")

    def water_pour(prefix,quantity):
        approach("right",(230,150,h+120),prefix+"_approach","water")
        arm("right",(230,150,h+120),opening=82,held="carafe")
        emit(prefix+"_pick","Pick up the water carafe","water")
        arm("right",(230,150,rim+125),opening=82,held="carafe")
        emit(prefix+"_lift","Lift the carafe clear of the vessels","water")
        pour_y = 190+35*math.sin(math.radians(60))
        arm("right",(110,pour_y,rim+125),opening=82,held="carafe")
        emit(prefix+"_carry","Carry water above the open cup","water")
        arm("right",(110,pour_y,rim+140),(30,0,0),82,"carafe")
        emit(prefix+"_tilt_mid","Lift while tilting clear of the cup rim","water")
        arm("right",(110,pour_y,rim+125),(60,0,0),82,"carafe")
        emit(prefix+"_tilt","Tilt the carafe above the cup","water")
        arm("right",(110,pour_y,rim+85),(60,0,0),82,"carafe")
        state["water_ml"] += quantity
        emit(prefix+"_pour",f"Pour {quantity:g} mL water","water",dispensing_ml=quantity,
             source="carafe",destination="blender_cup")
        arm("right",(110,pour_y,rim+125),(60,0,0),82,"carafe")
        emit(prefix+"_raise","Raise the tilted carafe clear","water")
        arm("right",(110,pour_y,rim+140),(30,0,0),82,"carafe")
        emit(prefix+"_recover_mid","Lift while recovering the carafe upright","water")
        arm("right",(110,pour_y,rim+125),opening=82,held="carafe")
        emit(prefix+"_upright","Return the carafe upright","water")
        arm("right",(230,150,rim+125),opening=82,held="carafe")
        emit(prefix+"_return_high","Carry the carafe above its resting position","water")
        arm("right",(230,150,h+120),opening=82,held="carafe")
        emit(prefix+"_return","Put the water carafe down","water")
        state["objects"]["carafe"]["held_by"] = None
        withdraw("right",prefix,"water")

    water_pour("initial_water",p.initial_water_ml)
    approach("left",scoop_rest,"scoop_approach","powder")
    arm("left",scoop_rest,opening=12,held="scoop")
    emit("scoop_pick","Pick up the measuring scoop","powder")
    arm("left",(-230,290,rim+40),opening=12,held="scoop")
    emit("scoop_first_lift","Lift the scoop clear before crossing the station","powder")
    for n in range(1,p.scoop_count+1):
        dip_angle = (-50,0,0)
        dip_bowl = (-110,190,h+105)
        dip_tcp = tuple(b-o for b,o in zip(dip_bowl,rotate((0,65,0),dip_angle)))
        arm("left",(dip_tcp[0],dip_tcp[1],h+205),dip_angle,12,"scoop")
        emit(f"scoop_{n}_approach","Approach the jar through its open rim","powder")
        arm("left",dip_tcp,dip_angle,12,"scoop")
        emit(f"scoop_{n}_dip",f"Measure scoop {n} of {p.scoop_count}","powder",scoop_event="dip")
        arm("left",(-110,140,h+160),opening=12,held="scoop")
        emit(f"scoop_{n}_lift","Lift the level scoop clear of the container","powder")
        arm("left",(110,125,rim+40),opening=12,held="scoop")
        emit(f"scoop_{n}_carry","Move the level scoop above the cup","powder")
        yaw = 180-math.degrees(math.atan2(110+p.shoulder_span_mm/2,190-p.shoulder_forward_mm))
        twist = (0,0,yaw)
        level_bowl = (110,190,rim+40)
        level_tcp = tuple(b-o for b,o in zip(level_bowl,rotate((0,65,0),twist)))
        arm("left",level_tcp,twist,12,"scoop")
        emit(f"scoop_{n}_orient","Orient the scoop away from the forearm","powder")
        angles = (-120,0,yaw)
        bowl = (110,190,rim+25)
        tcp = tuple(b-o for b,o in zip(bowl,rotate((0,65,0),angles)))
        arm("left",tcp,angles,12,"scoop")
        state["powder_scoops"] += 1
        emit(f"scoop_{n}_tip",f"Tip scoop {n} into the blender","powder",scoop_event="dispense",
             dispensing_ml=p.scoop_ml,source="scoop",destination="blender_cup")
        arm("left",level_tcp,twist,12,"scoop")
        emit(f"scoop_{n}_upright","Recover the scoop upright above the cup","powder")
        arm("left",(110,125,rim+40),opening=12,held="scoop")
        emit(f"scoop_{n}_reset_yaw","Return the level scoop to its carry orientation","powder")
        arm("left",(-230,290,rim+40),opening=12,held="scoop")
        emit(f"scoop_{n}_return_high","Carry the scoop clear of the jar","powder")
    arm("left",scoop_rest,opening=12,held="scoop")
    emit("scoop_return","Return the scoop to its stand","powder")
    state["objects"]["scoop"]["held_by"] = None
    withdraw("left","scoop","powder")
    water_pour("top_up",plan["top_up_water_ml"])

    approach("right",(250,285,h+35),"cap_approach","close_blender")
    arm("right",(250,285,h+35),opening=cap_diameter,held="blender_lid")
    emit("cap_retrieve","Retrieve the blender cap","close_blender")
    arm("right",(250,285,rim+65),opening=cap_diameter,held="blender_lid")
    emit("cap_lift","Lift the cap above the vessels","close_blender")
    arm("right",(110,190,rim+65),opening=cap_diameter,held="blender_lid")
    emit("cap_carry","Carry the cap over the blender axis","close_blender")
    lifted = p.cap_turns*p.blender_thread_pitch_mm
    arm("right",(110,190,blender_cap_z+lifted),opening=cap_diameter,held="blender_lid")
    emit("cap_align","Align the cap and thread axis","close_blender")
    for fraction in (.125,.25,.375,.5,.625,.75,.875,1):
        turns = p.cap_turns*fraction
        lift = lifted-turns*p.blender_thread_pitch_mm
        arm("right",(110,190,blender_cap_z+lift),(0,0,-turns*360),cap_diameter,"blender_lid")
        emit(f"cap_close_{fraction}","Screw the cap down with a limited torque policy","close_blender",
             thread={"object":"blender_lid","turns":turns,"axial_lift_mm":lift})
    state["planned_torque_nm"] = p.cap_target_torque_nm
    state["blender_open"] = False
    state["objects"]["blender_lid"]["held_by"] = None
    emit("cap_seated","Cap seated; stop at the torque target","close_blender")
    withdraw("right","cap","close_blender")
    state["human_ready"] = True
    emit("human_ready","Ready for the human to blend and enjoy","handoff",
         "Your shake is ready to blend. Please press the blender button, then enjoy!")
    return frames
