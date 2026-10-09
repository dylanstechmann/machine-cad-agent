"""Pocket Pal: original handheld-inspired shell, articulated limbs and fixtures."""

import math
from dataclasses import dataclass, replace

import cadquery as cq
from .kinematics import link_location, solve_arm, solve_leg, tool_location
from .sequence import make_sequence

PURPLE = (.42,.27,.78,1)
CREAM = (.87,.90,.85,1)
DARK = (.09,.14,.21,1)
MINT = (.38,.93,.71,1)
CORAL = (.96,.39,.36,1)
GOLD = (.98,.72,.24,1)
BLUE = (.22,.60,.84,1)


@dataclass
class Component:
    name: str
    shape: cq.Shape
    loc: cq.Location
    category: str
    description: str
    group: str = "stationary"
    color: tuple = CREAM

    def world(self):
        return self.shape.located(self.loc)


def box(x,y,z):
    return cq.Workplane("XY").box(x,y,z).val()


def cylinder(radius,height):
    return cq.Workplane("XY").circle(radius).extrude(height).val()


def ring(outer,inner,height):
    return cq.Workplane("XY").circle(outer).circle(inner).extrude(height).val()


def link(length):
    result = cq.Workplane("XY").box(18,20,length-20).translate((0,0,length/2))
    for z in (0,length):
        pad = cq.Workplane("YZ").circle(14).extrude(10,both=True).translate((0,0,z))
        bore = cq.Workplane("YZ").circle(4.5).extrude(15,both=True).translate((0,0,z))
        result = result.union(pad).cut(bore)
    return result.val()


def digit_segment(length,width,depth):
    """Rounded phalanx centered halfway down local -Z from its knuckle."""
    return (cq.Workplane("XY").box(width,depth,length).edges("|Z")
            .fillet(min(width,depth)/3).translate((0,0,-length/2)).val())


def rounded_foot(width,length,depth):
    radius = min(8,width/3,length/3)
    return cq.Workplane("XY").box(width,length,depth).edges("|Z").fillet(radius).translate((0,0,-depth/2)).val()


def hand_digit_locations(p,side,opening):
    """Kinematic five-digit hand curl driven by the sequence's aperture command."""
    sign = -1 if side=="left" else 1
    closure = max(0.0,min(1.0,1.0-opening/p.gripper_max_opening_mm))
    base_z = p.tool_offset_mm-p.hand_palm_length_mm/2
    proximal = p.finger_phalanx_length_mm
    distal = proximal*.78
    result = {}

    def add_digit(name,base_x,base_y,base_z,first_angle,second_angle,width):
        base = (base_x,base_y,base_z)
        first = tool_location(base,(0,first_angle,0))
        pip = first*tool_location((0,0,-proximal))
        second = tool_location(base,(0,first_angle+second_angle,0))*tool_location((0,0,-proximal))
        result[f"digit_{side}_{name}_proximal"] = first
        result[f"digit_{side}_{name}_distal"] = second
        result[f"knuckle_{side}_{name}_mcp"] = tool_location(base)
        result[f"knuckle_{side}_{name}_pip"] = pip
        return width

    finger_offsets = (2,14,26,44)
    finger_depths = (-8,-3,3,8)
    finger_names = ("index","middle","ring","pinky")
    for name,x,y in zip(finger_names,finger_offsets,finger_depths):
        angle = sign*(-45+80*closure)
        pip_angle = sign*30*closure
        add_digit(name,sign*x,y,base_z,angle,pip_angle,10)

    thumb_angle = sign*(45-90*closure)
    thumb_pip_angle = -sign*20*closure
    add_digit("thumb",-sign*(p.hand_palm_width_mm*.43),0,base_z+3,
              thumb_angle,thumb_pip_angle,13)
    return result


def cup(radius,height,wall):
    return (cq.Workplane("XY").circle(radius+wall).extrude(height+wall)
            .cut(cq.Workplane("XY").circle(radius).extrude(height+1).translate((0,0,wall))).val())


def lid(radius,inner):
    return (cq.Workplane("XY").circle(radius).extrude(14).translate((0,0,-7))
            .cut(cq.Workplane("XY").circle(inner).extrude(11).translate((0,0,-7)))).val()


def scoop(p):
    r = (3*p.scoop_ml*1000/(2*math.pi))**(1/3)
    outer = cq.Workplane("XY").sphere(r+2.5).intersect(
        cq.Workplane("XY").box(100,100,r+2.5).translate((0,0,-(r+2.5)/2)))
    handle = cq.Workplane("XY").box(12,65-r+5,6).translate((0,-(65+r-5)/2,-3))
    result = outer.union(handle).cut(cq.Workplane("XY").sphere(r))
    return result.translate((0,65,0)).val()


def templates(p):
    parts = []
    def add(name,shape,position=(0,0,0),category="printable-study",description="Nominal mechanism part",
            group="stationary",color=CREAM):
        parts.append(Component(name,shape,tool_location(position),category,description,group,color))

    wall = p.shell_wall_mm
    center_z = p.hip_height_mm+20+p.body_height_mm/2
    shell = (cq.Workplane("XY").box(p.body_width_mm,p.body_depth_mm,p.body_height_mm).edges("|Y").fillet(12)
             .cut(cq.Workplane("XY").box(p.body_width_mm-2*wall,p.body_depth_mm,
                                       p.body_height_mm-2*wall).edges("|Y").fillet(9).translate((0,wall,0)))).val()
    add("shell_back",shell,(0,0,center_z),description="Rounded hollow console shell; no copied brand assets",group="body",color=PURPLE)
    face = cq.Workplane("XY").box(p.body_width_mm,5,p.body_height_mm).edges("|Y").fillet(12)
    face = face.cut(cq.Workplane("XY").box(137,20,94).translate((0,0,45)))
    for x,z in ((36,-65),(47,-60),(58,-55),(69,-50),(40,-76),(51,-71),(62,-66),(73,-61)):
        face = face.cut(cq.Workplane("XZ").center(x,z).circle(2).extrude(10,both=True))
    front = p.body_depth_mm/2+2.5
    add("faceplate",face.val(),(0,front,center_z),group="body",color=PURPLE)
    bezel = (cq.Workplane("XY").box(149,8,105).edges("|Y").fillet(8)
             .cut(cq.Workplane("XY").box(130,12,86).edges("|Y").fillet(4))).val()
    add("screen_bezel",bezel,(0,front+3,center_z+45),group="body",color=DARK)
    add("screen_panel",box(130,3,86),(0,front+4,center_z+45),"display-envelope","Expressive display envelope","body",(.14,.25,.28,1))
    for side,x in (("left",-25),("right",25)):
        add("eye_"+side,box(12,2,23),(x,front+6.5,center_z+54),group="body",color=MINT)
    smile = (cq.Workplane("XZ").moveTo(-22,0).threePointArc((0,-9),(22,0)).lineTo(20,3)
             .threePointArc((0,-5),(-20,3)).close().extrude(2)).val()
    add("smile",smile,(0,front+8,center_z+31),group="body",color=MINT)
    dpad = cq.Workplane("XY").box(32,7,10).union(cq.Workplane("XY").box(10,7,32)).val()
    add("d_pad",dpad,(-47,front+6,center_z-44),group="body",color=DARK)
    for name,x,z in (("button_a",55,-33),("button_b",30,-48)):
        button = cq.Workplane("XZ").circle(9).extrude(7).val()
        add(name,button,(x,front+10,center_z+z),group="body",color=CORAL)
    for name,x in (("start_button",14),("select_button",-10)):
        add(name,box(17,6,5),(x,front+6,center_z-79),group="body",color=DARK)
    add("speaker_envelope",box(42,14,24),(48,20,center_z-67),"purchased-envelope",
        "Speaker packaging envelope; browser narration is separate","body",DARK)
    add("battery_envelope",box(100,32,40),(0,-10,center_z-50),"purchased-envelope",
        "Nominal rechargeable battery packaging; electrical system unspecified","body",DARK)
    add("hip_bridge",box(160,54,30),(0,0,p.hip_height_mm+10),group="body",color=DARK)
    for side,sign in (("left",-1),("right",1)):
        x = sign*p.shoulder_span_mm/2
        add("shoulder_mount_"+side,box(35,p.shoulder_forward_mm+10,27),
            (x,p.shoulder_forward_mm/2,p.shoulder_height_mm),group="body",color=GOLD)
        shoulder_ball = cq.Workplane("XY").sphere(16).val()
        add("shoulder_mount_ball_"+side,shoulder_ball,
            (x,p.shoulder_forward_mm,p.shoulder_height_mm),group="body",color=GOLD)
        add("upper_arm_"+side,link(p.arm_upper_mm).translate((-sign*11,0,0)),group="upper_"+side)
        add("forearm_"+side,link(p.arm_lower_mm).translate((sign*11,0,0)),group="fore_"+side,color=PURPLE)
        for joint,group in (("shoulder","upper_"),("elbow","fore_")):
            pin = cq.Workplane("YZ").circle(4.2).extrude(24,both=True).val()
            add(joint+"_pin_"+side,pin,category="purchased-envelope",description="Nominal pivot pin",group=group+side,color=GOLD)
        elbow_ball = cq.Workplane("XY").sphere(13).val()
        add("elbow_joint_"+side,elbow_ball,group="fore_"+side,color=GOLD)
        stem = cylinder(12,23).translate((0,0,p.tool_offset_mm-10))
        add("wrist_"+side,stem,group="tool_"+side,color=GOLD)
        palm = cq.Workplane("XY").box(p.hand_palm_width_mm,p.hand_palm_depth_mm,p.hand_palm_length_mm).edges("|Z").fillet(9).translate((0,0,p.tool_offset_mm)).val()
        add("palm_"+side,palm,description="Robotic palm envelope; anthropomorphic digits are articulated in the kinematic hand study",group="tool_"+side,color=DARK)
        wrist_ball = cq.Workplane("XY").sphere(13).translate((0,0,p.tool_offset_mm)).val()
        add("wrist_joint_"+side,wrist_ball,group="tool_"+side,color=GOLD)
        for digit,width in (("index",10),("middle",10),("ring",10),("pinky",10),("thumb",13)):
            for segment,length,depth in (("proximal",p.finger_phalanx_length_mm,width),
                                         ("distal",p.finger_phalanx_length_mm*.78,width-1)):
                add(f"digit_{side}_{digit}_{segment}",digit_segment(length,depth,15),
                    description="Separate articulated finger phalanx; joint travel is a CAD pose heuristic",
                    group=f"digit_{side}_{digit}_{segment}",color=CREAM if digit!="thumb" else CORAL)
            knuckle = cq.Workplane("XY").sphere(5.5 if digit!="thumb" else 6.5).val()
            for joint in ("mcp","pip"):
                add(f"knuckle_{side}_{digit}_{joint}",knuckle,
                    description="Visible finger hinge envelope; no selected actuator or measured force",
                    group=f"knuckle_{side}_{digit}_{joint}",color=GOLD)
        add("upper_leg_"+side,link(p.leg_upper_mm).translate((11,0,0)),group="thigh_"+side,color=PURPLE)
        add("lower_leg_"+side,link(p.leg_lower_mm).translate((-11,0,0)),group="shin_"+side)
        hip_ball = cq.Workplane("XY").sphere(17).val()
        add("hip_joint_"+side,hip_ball,(sign*55,0,p.hip_height_mm),group="body",color=GOLD)
        knee_ball = cq.Workplane("XY").sphere(15).val()
        add("knee_joint_"+side,knee_ball,group="shin_"+side,color=GOLD)
        ankle_ball = cq.Workplane("XY").sphere(12).val()
        add("ankle_joint_"+side,ankle_ball,group="foot_"+side,color=GOLD)
        for joint,group in (("hip","thigh_"),("knee","shin_")):
            pin = cq.Workplane("YZ").circle(4.2).extrude(22,both=True).val()
            add(joint+"_pin_"+side,pin,category="purchased-envelope",description="Nominal planar leg pivot pin",group=group+side,color=GOLD)
        foot = rounded_foot(68,70,20)
        add("foot_"+side,foot,group="foot_"+side,color=GOLD)
        toe_names = ("big","second","middle","fourth","little")
        toe_offsets = (20,9,-2,-13,-24) if side=="left" else (-20,-9,2,13,24)
        for index,(name,x_offset) in enumerate(zip(toe_names,toe_offsets)):
            toe_width = (14,11,11,10,9)[index]
            toe = rounded_foot(toe_width,p.toe_length_mm*.58,14)
            tip = rounded_foot(toe_width*.82,p.toe_length_mm*.48,12)
            add(f"toe_{side}_{name}_base",toe.translate((x_offset,38,-10)),
                description="Separate modeled toe phalanx; fixed to the foot in this gait study",group="toe_"+side,color=CREAM)
            add(f"toe_{side}_{name}_tip",tip.translate((x_offset,38+p.toe_length_mm*.46,-10)),
                description="Distal toe segment with visible hinge separation",group="toe_"+side,color=PURPLE)
            toe_joint = cq.Workplane("XY").sphere(4.5).translate((x_offset,38,-10)).val()
            add(f"toe_{side}_{name}_joint",toe_joint,
                description="Toe hinge envelope; toe flexion is not dynamically actuated",group="toe_"+side,color=GOLD)

    h = p.bench_height_mm
    add("worktop",box(640,360,12),(0,245,h-6),"fixture-study","Preparation station with front clearance for hips and legs",color=(.70,.77,.78,1))
    for x in (-280,280):
        for y in (90,380):
            add(f"bench_leg_{x}_{y}",box(20,20,h-12),(x,y,(h-12)/2),"fixture-study",color=DARK)
    add("protein_jar",cup(55,127,3),(-110,190,h),"vessel-envelope","Nominal vegan protein container",color=(.66,.82,.42,1))
    add("jar_lid",lid(60,58.5),category="vessel-envelope",description="Nominal cap envelope; thread path is kinematic",group="object_jar_lid",color=GOLD)
    add("jar_lid_marker",box(40,5,2).translate((10,0,7)),category="display-envelope",
        description="Asymmetric cap rotation marker",group="object_jar_lid",color=DARK)
    add("blender_base",cylinder(p.blender_internal_radius_mm+p.vessel_wall_mm+2,p.blender_base_height_mm),
        (110,190,h),"purchased-envelope","Portable battery blender motor/base envelope",color=DARK)
    add("blender_cup",cup(p.blender_internal_radius_mm,p.blender_internal_height_mm,p.vessel_wall_mm),
        (110,190,h+p.blender_base_height_mm),"vessel-envelope","Measured cylindrical cavity, nominal portable blender",color=(.50,.81,.94,.25))
    add("blender_lid",lid(p.blender_internal_radius_mm+p.vessel_wall_mm+2,p.blender_internal_radius_mm+p.vessel_wall_mm+.5),
        category="vessel-envelope",description="Nominal cap envelope; purchased thread profile is unspecified",group="object_blender_lid",color=BLUE)
    add("blender_lid_marker",box(28,5,2).translate((8,0,7)),category="display-envelope",
        description="Asymmetric cap rotation marker",group="object_blender_lid",color=DARK)
    button = cq.Workplane("XZ").circle(7).extrude(4).val()
    add("blender_power_button",button,(110,190+p.blender_internal_radius_mm+6,h+16),"purchased-envelope",
        "Only the independent human operates this button",color=CORAL)
    add("carafe",cup(38,152,3).translate((0,0,-120)),category="vessel-envelope",
        description="Open water carafe, 35 mm mouth offset from grip",group="object_carafe",color=(.5,.8,.95,.3))
    add("scoop",scoop(p),description="Hemispherical measured bowl with grippable handle",group="object_scoop",color=GOLD)
    for name,x,inner,outer in (("jar_fixture",-110,58.5,65),("blender_fixture",110,p.blender_internal_radius_mm+p.vessel_wall_mm+2.5,
                                                               p.blender_internal_radius_mm+p.vessel_wall_mm+9)):
        add(name,ring(outer,inner,20),(x,190,h),"fixture-study","Counter-torque fixture envelope; mounting force unmeasured",color=CORAL)
    for name,position,radius,height in (("jar_lid_stand",(-230,105,h),50,44),
                                       ("blender_lid_stand",(250,285,h),35,28)):
        stand = cq.Workplane("XY").circle(18).extrude(height-5).union(
            cq.Workplane("XY").circle(radius).extrude(5).translate((0,0,height-5))).val()
        add(name,stand,position,"fixture-study","Raised cap parking pad",color=(.5,.58,.64,1))
    holder = box(24,20,49).translate((0,0,24.5))
    add("scoop_stand",holder,(-230,315,h),"fixture-study","Support under the handle beyond the gripper fingers",color=(.5,.58,.64,1))
    return parts


def pose_parts(parts,p,frame,include_visualization=True):
    arms = {s:solve_arm(p,s,a["tcp_mm"],a["euler_deg"],frame["body_y_mm"]) for s,a in frame["arms"].items()}
    legs = {s:solve_leg(p,s,frame["feet"][s],frame["body_y_mm"]) for s in ("left","right")}
    digits = {s:hand_digit_locations(p,s,frame["arms"][s]["opening_mm"]) for s in ("left","right")}
    if not all(v["reachable"] for v in (*arms.values(),*legs.values())):
        raise ValueError("Pose has an unreachable limb target; no clamped pose is rendered")
    result = []
    for part in parts:
        group,loc = part.group,part.loc
        if group=="body":
            loc = tool_location((0,frame["body_y_mm"],0))*loc
        for side in ("left","right"):
            a,l = arms[side],legs[side]
            if group=="upper_"+side: loc = link_location(a["shoulder_mm"],a["elbow_mm"],a["hinge_axis"])
            elif group=="fore_"+side: loc = link_location(a["elbow_mm"],a["wrist_mm"],a["hinge_axis"])
            elif group=="tool_"+side: loc = tool_location(frame["arms"][side]["tcp_mm"],frame["arms"][side]["euler_deg"])
            elif group in digits[side]:
                loc = tool_location(frame["arms"][side]["tcp_mm"],frame["arms"][side]["euler_deg"])*digits[side][group]
            elif group=="thigh_"+side: loc = link_location(l["hip_mm"],l["knee_mm"],(1,0,0))
            elif group=="shin_"+side: loc = link_location(l["knee_mm"],l["ankle_mm"],(1,0,0))
            elif group=="foot_"+side: loc = tool_location(l["ankle_mm"])
            elif group=="toe_"+side: loc = tool_location(l["ankle_mm"])
        if group.startswith("object_"):
            obj = frame["objects"][group.removeprefix("object_")]
            loc = tool_location(obj["position_mm"],obj["euler_deg"])
        result.append(replace(part,loc=loc))
    h = p.bench_height_mm
    if include_visualization and frame["fill_ml"]>0:
        height = min(p.blender_internal_height_mm,frame["fill_ml"]*1000/(math.pi*p.blender_internal_radius_mm**2))
        liquid = cylinder(p.blender_internal_radius_mm-.3,max(.5,height))
        result.append(Component("shake_volume_preview",liquid,tool_location((110,190,h+p.blender_base_height_mm+p.vessel_wall_mm)),
                                "visualization","Volume illustration, not fluid dynamics",color=(.84,.76,.57,.85)))
    carafe_remaining = max(0,p.water_available_ml-frame["water_ml"])
    if include_visualization and carafe_remaining:
        height = min(152,carafe_remaining*1000/(math.pi*38**2))
        obj = frame["objects"]["carafe"]
        loc = tool_location(obj["position_mm"],obj["euler_deg"])*tool_location((0,0,-117))
        result.append(Component("carafe_water_preview",cylinder(37.7,height),loc,
                                "visualization","Stylized fill volume, not simulated free surface",color=(.28,.68,.94,.7)))
    return result


def generate(p):
    return pose_parts(templates(p),p,make_sequence(p)[5])


def assembly(parts):
    result = cq.Assembly(name="Pocket_Pal")
    for part in parts:
        result.add(part.shape,name=part.name,loc=part.loc,color=cq.Color(*part.color))
    return result
