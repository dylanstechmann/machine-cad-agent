"""Analytic position IK and explicit rigid tool transforms, all in mm."""

import math
import cadquery as cq


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def rotate(v, angles):
    """Extrinsic X, Y, Z Euler rotations, matching tool_location."""
    x, y, z = v
    ax, ay, az = map(math.radians, angles)
    y, z = y*math.cos(ax)-z*math.sin(ax), y*math.sin(ax)+z*math.cos(ax)
    x, z = x*math.cos(ay)+z*math.sin(ay), -x*math.sin(ay)+z*math.cos(ay)
    x, y = x*math.cos(az)-y*math.sin(az), x*math.sin(az)+y*math.cos(az)
    return x, y, z


def tool_location(position, angles=(0,0,0)):
    loc = cq.Location(cq.Vector(*position))
    for axis, angle in (((0,0,1),angles[2]),((0,1,0),angles[1]),((1,0,0),angles[0])):
        loc = loc*cq.Location(cq.Vector(),cq.Vector(*axis),angle)
    return loc


def link_location(start, end,hinge_axis=None):
    direction = cq.Vector(*sub(end,start)).normalized()
    tangent = cq.Vector(*hinge_axis) if hinge_axis else cq.Vector(-direction.y,direction.x,0)
    if tangent.Length < 1e-8:
        tangent = cq.Vector(1,0,0)
    return cq.Location(cq.Plane(origin=start,xDir=tangent,normal=direction))


def solve_arm(p, side, tcp, angles=(0,0,0), body_y=0):
    shoulder = ((-1 if side=="left" else 1)*p.shoulder_span_mm/2,
                body_y+p.shoulder_forward_mm,p.shoulder_height_mm)
    wrist = add(tcp,rotate((0,0,p.tool_offset_mm),angles))
    dx,dy,dz = sub(wrist,shoulder)
    radial,distance = math.hypot(dx,dy),norm((dx,dy,dz))
    a,b = p.arm_upper_mm,p.arm_lower_mm
    if distance > a+b+1e-7 or distance < abs(a-b)-1e-7 or distance < 1e-8:
        return {"reachable":False,"distance_mm":distance,"maximum_mm":a+b,
                "tcp_mm":list(tcp),"wrist_mm":list(wrist),"shoulder_mm":list(shoulder)}
    yaw = math.atan2(dy,dx)
    pitch = math.atan2(dz,radial)+math.acos(max(-1,min(1,(a*a+distance*distance-b*b)/(2*a*distance))))
    elbow_angle = -math.acos(max(-1,min(1,(distance*distance-a*a-b*b)/(2*a*b))))
    elbow = add(shoulder,(a*math.cos(pitch)*math.cos(yaw),a*math.cos(pitch)*math.sin(yaw),a*math.sin(pitch)))
    fk_wrist = add(elbow,(b*math.cos(pitch+elbow_angle)*math.cos(yaw),
                         b*math.cos(pitch+elbow_angle)*math.sin(yaw),b*math.sin(pitch+elbow_angle)))
    fk_tcp = sub(fk_wrist,rotate((0,0,p.tool_offset_mm),angles))
    return {"reachable":True,"shoulder_mm":list(shoulder),"elbow_mm":list(elbow),
            "wrist_mm":list(fk_wrist),"tcp_mm":list(fk_tcp),"target_tcp_mm":list(tcp),
            "position_error_mm":norm(sub(fk_tcp,tcp)),"distance_mm":distance,
            "hinge_axis":[-math.sin(yaw),math.cos(yaw),0],
            "joints_deg":{"shoulder_yaw":math.degrees(yaw),"shoulder_pitch":math.degrees(pitch),
                          "elbow_pitch":math.degrees(elbow_angle)},
            "tool_euler_deg":list(angles),"wrist_orientation_mode":"three-axis gimbal, world tool orientation"}


def solve_leg(p, side, ankle, body_y=0):
    hip = ((-1 if side=="left" else 1)*55,body_y,p.hip_height_mm)
    dy,down = ankle[1]-hip[1],hip[2]-ankle[2]
    distance = math.hypot(dy,down)
    a,b = p.leg_upper_mm,p.leg_lower_mm
    if abs(ankle[0]-hip[0])>1e-7 or distance < 1e-8 or distance > a+b+1e-7 or distance < abs(a-b)-1e-7:
        return {"reachable":False,"distance_mm":distance}
    angle = math.atan2(dy,down)+math.acos(max(-1,min(1,(a*a+distance*distance-b*b)/(2*a*distance))))
    knee = (hip[0],hip[1]+a*math.sin(angle),hip[2]-a*math.cos(angle))
    return {"reachable":True,"hip_mm":list(hip),"knee_mm":list(knee),"ankle_mm":list(ankle),
            "floor_clearance_mm":ankle[2]-20,"mode":"sagittal kinematics; no balance/dynamics claim"}
