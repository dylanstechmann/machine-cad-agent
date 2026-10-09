"""Motor-driven supported-arm physics and a bounded PPO learning curriculum.

Meters, kilograms, seconds and radians inside MuJoCo; mm in user reports.
This model is a reduced mechanism study, not a digital twin of purchased hardware.
"""

import hashlib
import copy
import importlib.metadata
import json
import math
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces
from PIL import Image

from .hardware import hardware_reference, physical_readiness
from .kinematics import solve_arm
from .parameters import load_parameters
from .pipeline import source_digest, write_json

RUN_ID = re.compile(r"^reach-[a-f0-9]{16}$")


def load_simulation(root):
    cfg = json.loads((root/"configs"/"simulation.json").read_text(encoding="utf-8"))
    if cfg["task"] != "supported_right_arm_wrist_reach": raise ValueError("Unknown simulation task")
    if cfg["timestep_s"] <= 0 or not 1 <= cfg["physics_steps_per_action"] <= 50:
        raise ValueError("Invalid simulation timestep or substep count")
    if not 1 <= cfg["hold_actions"] <= cfg["episode_actions"] <= 1000:
        raise ValueError("Invalid episode/hold duration")
    for key in ("motor_torque_limit_nm","position_gain_nm_per_rad","velocity_gain_nm_s_per_rad"):
        if len(cfg[key]) != 3 or not all(math.isfinite(v) and v > 0 for v in cfg[key]):
            raise ValueError("Expected three positive finite values for " + key)
    for key in ("target_tolerance_mm","joint_target_velocity_rad_s","upper_link_mass_kg","lower_link_mass_kg","wrist_payload_mass_kg","max_joint_speed_rad_s","unexpected_contact_force_limit_n"):
        if not math.isfinite(cfg[key]) or cfg[key]<=0: raise ValueError("Expected positive finite " + key)
    for key in ("target_center_relative_to_blender_top_mm","target_half_extent_mm"):
        if len(cfg[key])!=3 or not all(math.isfinite(v) for v in cfg[key]): raise ValueError("Invalid target geometry")
    if any(v<=0 for v in cfg["target_half_extent_mm"]): raise ValueError("Target ranges must be positive")
    if len(cfg["joint_ranges_rad"])!=3 or any(len(v)!=2 or not all(math.isfinite(x) for x in v) or v[0]>=v[1] for v in cfg["joint_ranges_rad"]):
        raise ValueError("Invalid joint ranges")
    for key in ("mass_multiplier","torque_multiplier","friction_multiplier","joint_damping_multiplier"):
        values = cfg["randomization"][key]
        if len(values)!=2 or not all(math.isfinite(v) and v>0 for v in values) or values[0]>values[1]:
            raise ValueError("Invalid randomization for "+key)
    delay = cfg["randomization"]["control_delay_actions"]
    if len(delay)!=2 or not all(type(v) is int and 0<=v<=10 for v in delay) or delay[0]>delay[1]: raise ValueError("Invalid control delay")
    return cfg


def mjcf(p, cfg, reference):
    """Primitive collision proxies preserve CAD shoulder position/link lengths.

    Inertias are explicit assumed link/payload masses; visual geoms add no mass.
    The blender cylinder uses advertised outside dimensions, not a cup cavity.
    """
    m = lambda v: v/1000
    document = ET.Element("mujoco", model="Pocket_Pal_supported_arm_reach")
    ET.SubElement(document,"compiler",angle="radian",inertiafromgeom="false")
    ET.SubElement(document,"option",timestep=str(cfg["timestep_s"]),gravity="0 0 -9.81",integrator="implicitfast")
    visual = ET.SubElement(document,"visual")
    ET.SubElement(visual,"global",offwidth="960",offheight="720")
    default = ET.SubElement(document,"default")
    ET.SubElement(default,"joint",damping="0.08",armature="0.005",limited="true")
    ET.SubElement(default,"geom",friction="0.8 0.01 0.001",condim="3",rgba="0.55 0.4 0.85 1")
    world = ET.SubElement(document,"worldbody")
    ET.SubElement(world,"light",pos="0 -1 2",dir="0 0 -1",diffuse="0.9 0.9 0.9")
    ET.SubElement(world,"camera",name="overview",pos="0.95 -0.75 0.9",xyaxes="0.69 0.72 0 -0.34 0.32 0.88")
    def geom(parent, name, typ, size, pos="0 0 0", **kwargs):
        return ET.SubElement(parent,"geom",name=name,type=typ,size=size,pos=pos,**kwargs)
    geom(world,"floor","plane","1 1 .01",rgba=".87 .88 .91 1")
    geom(world,"supported_pedestal","box",".08 .07 .085",pos="0 0 .085",rgba=".28 .3 .35 1")
    geom(world,"torso","box",f"{m(p.body_width_mm/2)} {m(p.body_depth_mm/2)} {m(p.body_height_mm/2)}",
         pos=f"0 0 {m(p.hip_height_mm+20+p.body_height_mm/2)}",rgba=".35 .14 .8 1")
    geom(world,"screen","box",".065 .005 .04",pos=f"0 {m(p.body_depth_mm/2+5)} {m(p.hip_height_mm+p.body_height_mm*.72)}",rgba=".04 .19 .19 1",contype="0",conaffinity="0")
    geom(world,"bench","box",".32 .18 .006",pos=f"0 .245 {m(p.bench_height_mm-6)}",rgba=".62 .72 .73 1")
    for x in (-.28,.28):
        for y in (.09,.38):
            geom(world,f"bench_leg_{x}_{y}","box",f".01 .01 {m((p.bench_height_mm-12)/2)}",pos=f"{x} {y} {m((p.bench_height_mm-12)/2)}",rgba=".2 .24 .3 1")
    blender = reference["blender"]
    height, radius = m(blender["overall_height_mm"]),m(blender["outer_diameter_mm"]/2)
    geom(world,"nij_outer_envelope","cylinder",f"{radius} {height/2}",pos=f".11 .19 {m(p.bench_height_mm)+height/2}",rgba=".94 .94 .88 1")
    # Orgain geometry is still the old nominal station envelope; no package-fit claim.
    geom(world,"orgain_nominal_obstacle","cylinder",f"{m(55+p.vessel_wall_mm)} .065",pos=f"-.11 .19 {m(p.bench_height_mm)+.065}",rgba=".46 .72 .19 1")
    center = np.array([.11,.19,m(p.bench_height_mm)+height])+np.array(cfg["target_center_relative_to_blender_top_mm"])/1000
    ET.SubElement(world,"site",name="goal",type="sphere",size=".012",pos=" ".join(map(str,center)),rgba=".2 .9 .5 .7")
    root = ET.SubElement(world,"body",name="shoulder_yaw_body",pos=f"{m(p.shoulder_span_mm/2)} {m(p.shoulder_forward_mm)} {m(p.shoulder_height_mm)}")
    ET.SubElement(root,"inertial",pos="0 0 0",mass=".04",diaginertia=".00002 .00002 .00002")
    def joint(parent,name,axis,index):
        return ET.SubElement(parent,"joint",name=name,type="hinge",axis=axis,range=" ".join(map(str,cfg["joint_ranges_rad"][index])))
    joint(root,"shoulder_yaw","0 0 1",0)
    geom(root,"yaw_housing","sphere",".012",rgba=".9 .65 .18 1")
    upper = ET.SubElement(root,"body",name="upper_arm")
    joint(upper,"shoulder_pitch","0 -1 0",1)
    a,b = m(p.arm_upper_mm),m(p.arm_lower_mm)
    def inertia(parent,mass,length):
        radial=.012
        axial=mass*radial*radial/2
        transverse=mass*(3*radial*radial+length*length)/12
        ET.SubElement(parent,"inertial",pos=f"{length/2} 0 0",mass=str(mass),diaginertia=f"{axial} {transverse} {transverse}")
    inertia(upper,cfg["upper_link_mass_kg"],a)
    geom(upper,"upper_link","capsule",".012",fromto=f"0 0 0 {a} 0 0")
    fore = ET.SubElement(upper,"body",name="forearm",pos=f"{a} 0 0")
    joint(fore,"elbow_pitch","0 -1 0",2)
    inertia(fore,cfg["lower_link_mass_kg"],b)
    geom(fore,"lower_link","capsule",".012",fromto=f"0 0 0 {b} 0 0",rgba=".8 .86 .64 1")
    wrist = ET.SubElement(fore,"body",name="wrist_payload",pos=f"{b} 0 0")
    ET.SubElement(wrist,"inertial",pos="0 0 0",mass=str(cfg["wrist_payload_mass_kg"]),diaginertia=".00005 .00005 .00005")
    geom(wrist,"wrist_payload_geom","sphere",".018",rgba=".95 .54 .18 1")
    ET.SubElement(wrist,"site",name="wrist",size=".004",rgba="1 .2 .2 1")
    actuators = ET.SubElement(document,"actuator")
    for name,limit in zip(("shoulder_yaw","shoulder_pitch","elbow_pitch"),cfg["motor_torque_limit_nm"]):
        ET.SubElement(actuators,"motor",name=name+"_motor",joint=name,gear="1",ctrllimited="true",ctrlrange=f"{-limit} {limit}",forcelimited="true",forcerange=f"{-limit} {limit}")
    return ET.tostring(document,encoding="unicode")


class WristReachEnv(gym.Env):
    """Normalized motor position commands produce torques; qpos never teleports in step."""
    metadata = {"render_modes":["rgb_array"],"render_fps":50}

    def __init__(self,root: Path,snapshot=None):
        super().__init__()
        self.root = root
        if snapshot is None: snapshot=(load_parameters(root),load_simulation(root),hardware_reference(root))
        self.p,self.cfg,self.reference = copy.deepcopy(snapshot)
        self.xml = mjcf(self.p,self.cfg,self.reference)
        self.model = mujoco.MjModel.from_xml_string(self.xml)
        self.data = mujoco.MjData(self.model)
        self.qadr = self.model.jnt_qposadr.copy()
        self.vadr = self.model.jnt_dofadr.copy()
        self.wrist_id = mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_SITE,"wrist")
        self.goal_id = mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_SITE,"goal")
        self.center = self.model.site_pos[self.goal_id].copy()
        self.home = self.ik(self.center)
        self.command_span = .5
        self.action_space = spaces.Box(-1.,1.,shape=(3,),dtype=np.float32)
        self.observation_space = spaces.Box(-np.inf,np.inf,shape=(15,),dtype=np.float32)
        self.base_mass,self.base_inertia = self.model.body_mass.copy(),self.model.body_inertia.copy()
        self.base_damping,self.base_friction = self.model.dof_damping.copy(),self.model.geom_friction.copy()
        self.base_effort = np.array(self.cfg["motor_torque_limit_nm"])
        self.ranges = np.array(self.cfg["joint_ranges_rad"])
        self.kp,self.kd = np.array(self.cfg["position_gain_nm_per_rad"]),np.array(self.cfg["velocity_gain_nm_s_per_rad"])
        self.renderer = None

    def ik(self,goal):
        tcp = np.array(goal)*1000-np.array([0,0,self.p.tool_offset_mm])
        solved = solve_arm(self.p,"right",tcp)
        if not solved["reachable"]: raise ValueError("Simulation target outside the CAD arm reach")
        return np.radians(list(solved["joints_deg"].values()))

    def obs(self):
        wrist = self.data.site_xpos[self.wrist_id]
        return np.concatenate((self.data.qpos[self.qadr]-self.home,self.data.qvel[self.vadr]/6,
            (self.goal-self.center)*10,(self.goal-wrist)*10,(self.command-self.data.qpos[self.qadr]))).astype(np.float32)

    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model,self.data)
        random = self.cfg["randomization"]
        sample = lambda name: float(self.np_random.uniform(*random[name]))
        self.domain = {name:sample(name) for name in ("mass_multiplier","torque_multiplier","friction_multiplier","joint_damping_multiplier")}
        delay = random["control_delay_actions"]
        self.domain["control_delay_actions"] = int(self.np_random.integers(delay[0],delay[1]+1))
        self.action_queue = [np.zeros(3) for _ in range(self.domain["control_delay_actions"])]
        self.unpowered = False
        self.model.body_mass[:] = self.base_mass*self.domain["mass_multiplier"]
        self.model.body_inertia[:] = self.base_inertia*self.domain["mass_multiplier"]
        self.model.dof_damping[:] = self.base_damping*self.domain["joint_damping_multiplier"]
        self.model.geom_friction[:] = self.base_friction*self.domain["friction_multiplier"]
        self.limits = self.base_effort*self.domain["torque_multiplier"]
        self.model.actuator_ctrlrange[:] = np.column_stack((-self.limits,self.limits))
        self.model.actuator_forcerange[:] = np.column_stack((-self.limits,self.limits))
        mujoco.mj_setConst(self.model,self.data)
        self.goal = self.center+self.np_random.uniform(-1,1,3)*np.array(self.cfg["target_half_extent_mm"])/1000
        if options and "goal_m" in options: self.goal = np.asarray(options["goal_m"],dtype=float)
        self.ik(self.goal)  # Reject a configuration which randomizes outside reach.
        self.model.site_pos[self.goal_id] = self.goal
        self.data.qpos[self.qadr] = self.home+self.np_random.uniform(-random["initial_joint_noise_rad"],random["initial_joint_noise_rad"],3)
        self.command = self.data.qpos[self.qadr].copy()
        mujoco.mj_forward(self.model,self.data)
        self.actions,self.hold,self.physics_steps = 0,0,0
        self.peak_torque = np.zeros(3)
        self.saturated_substeps,self.contact_substeps,self.peak_contact,self.peak_speed = 0,0,0.,0.
        self.contacts = set()
        self.previous_error = float(np.linalg.norm(self.goal-self.data.site_xpos[self.wrist_id]))
        self.reason = "running"
        return self.obs(),{"domain":self.domain,"goal_m":self.goal.tolist()}

    def step(self,action):
        action = np.asarray(action,dtype=float)
        if action.shape!=(3,) or not np.isfinite(action).all(): raise ValueError("Expected three finite normalized actions")
        action = np.clip(action,-1,1)
        self.action_queue.append(action.copy())
        delayed_action = self.action_queue.pop(0)
        desired = np.clip(self.home+delayed_action*self.command_span,self.ranges[:,0],self.ranges[:,1])
        period = self.cfg["timestep_s"]*self.cfg["physics_steps_per_action"]
        self.command += np.clip(desired-self.command,-period*self.cfg["joint_target_velocity_rad_s"],period*self.cfg["joint_target_velocity_rad_s"])
        fatal = False
        for _ in range(self.cfg["physics_steps_per_action"]):
            torque = self.kp*(self.command-self.data.qpos[self.qadr])-self.kd*self.data.qvel[self.vadr]
            self.data.ctrl[:] = 0 if self.unpowered else np.clip(torque,-self.limits,self.limits)
            mujoco.mj_step(self.model,self.data)
            self.physics_steps += 1
            actual = np.abs(self.data.qfrc_actuator[self.vadr])
            self.peak_torque = np.maximum(self.peak_torque,actual)
            self.saturated_substeps += int(np.any(actual>=self.limits*.99))
            self.peak_speed = max(self.peak_speed,float(np.max(np.abs(self.data.qvel[self.vadr]))))
            self.contact_substeps += int(self.data.ncon>0)
            for i in range(self.data.ncon):
                force = np.zeros(6)
                mujoco.mj_contactForce(self.model,self.data,i,force)
                magnitude = float(np.linalg.norm(force[:3]))
                self.peak_contact = max(self.peak_contact,magnitude)
                contact = self.data.contact[i]
                self.contacts.add(tuple(sorted(self.model.geom(g).name for g in (contact.geom1,contact.geom2))))
            if not np.isfinite(self.data.qpos).all() or not np.isfinite(self.data.qvel).all(): self.reason="nonfinite_state";fatal=True
            elif any(w.number for w in self.data.warning): self.reason="simulator_warning";fatal=True
            elif self.peak_speed>self.cfg["max_joint_speed_rad_s"]: self.reason="joint_speed_limit";fatal=True
            elif self.peak_contact>self.cfg["unexpected_contact_force_limit_n"]: self.reason="unexpected_contact";fatal=True
            elif np.any(self.data.qpos[self.qadr]<self.ranges[:,0]-.03) or np.any(self.data.qpos[self.qadr]>self.ranges[:,1]+.03): self.reason="joint_range_limit";fatal=True
            if fatal: break
        mujoco.mj_forward(self.model,self.data)
        error = float(np.linalg.norm(self.goal-self.data.site_xpos[self.wrist_id]))
        self.actions += 1
        near = error<=self.cfg["target_tolerance_mm"]/1000 and np.max(np.abs(self.data.qvel[self.vadr]))<.5
        self.hold = self.hold+1 if near and not fatal else 0
        success = self.hold>=self.cfg["hold_actions"]
        if success: self.reason="success"
        truncated = self.actions>=self.cfg["episode_actions"] and not (fatal or success)
        if truncated: self.reason="time_limit"
        # Nonpositive dense reward avoids making a long near-miss worth more than early success.
        reward = math.exp(-25*error)-1+10*(self.previous_error-error)-.01*float(np.dot(action,action))
        if success: reward += 8
        if fatal: reward -= 100
        self.previous_error = error
        info = {"is_success":success,"error_mm":round(error*1000,4),"termination_reason":self.reason}
        if fatal or success or truncated: info["diagnostics"] = self.diagnostics()
        return self.obs(),reward,fatal or success,truncated,info

    def diagnostics(self):
        return {"goal_m":self.goal.tolist(),"wrist_m":self.data.site_xpos[self.wrist_id].tolist(),
            "domain":self.domain,"actions":self.actions,"physics_substeps":self.physics_steps,
            "motor_limits_nm":self.limits.tolist(),"peak_joint_torque_nm":self.peak_torque.tolist(),
            "saturation_fraction":self.saturated_substeps/max(1,self.physics_steps),
            "contact_substeps":self.contact_substeps,"contact_pairs":[list(v) for v in sorted(self.contacts)],
            "peak_contact_force_n":self.peak_contact,"peak_joint_speed_rad_s":self.peak_speed,
            "simulator_warnings":[{"type":i,"count":w.number} for i,w in enumerate(self.data.warning) if w.number]}

    def render(self):
        if self.renderer is None: self.renderer=mujoco.Renderer(self.model,height=480,width=640)
        self.renderer.update_scene(self.data,camera="overview")
        return self.renderer.render().copy()

    def close(self):
        if self.renderer: self.renderer.close();self.renderer=None


def run_directory(root,run_id=None):
    parent = (root/"builds"/"simulation").resolve()
    if run_id is None:
        latest = parent/"latest.json"
        if not latest.is_file(): raise ValueError("No simulation run yet. Run sim-train first.")
        run_id = json.loads(latest.read_text(encoding="utf-8"))["run_id"]
    if not RUN_ID.fullmatch(run_id): raise ValueError("Invalid simulation run ID")
    return parent/run_id


def read_simulation(root,run_id=None):
    directory = run_directory(root,run_id)
    report = json.loads((directory/"report.json").read_text(encoding="utf-8"))
    report["stale_source"] = report.get("source_changed_during_run",False) or report["source_sha256"]!=source_digest(root)
    return directory,report


def simulation_artifact(root,run_id,name):
    directory,report = read_simulation(root,run_id)
    entries = {entry["name"]:entry for entry in report["artifacts"]}
    if name not in entries: raise ValueError("Unknown simulation artifact")
    file = (directory/name).resolve()
    if not file.is_relative_to(directory) or not file.is_file(): raise ValueError("Invalid artifact path")
    data = file.read_bytes()
    entry = entries[name]
    if len(data)!=entry["bytes"] or hashlib.sha256(data).hexdigest()!=entry["sha256"]:
        raise ValueError("Simulation artifact integrity check failed")
    return file,report


def evaluate(env,policy,seeds,directory=None,record=False):
    episodes = []
    frames = []
    for episode,seed in enumerate(seeds):
        obs,_ = env.reset(seed=seed)
        env.unpowered = isinstance(policy,str) and policy=="unpowered"
        action_rng = np.random.default_rng(seed+500000)
        cumulative = 0.
        if record and episode==0: frames.append(Image.fromarray(env.render()))
        for step in range(env.cfg["episode_actions"]):
            if isinstance(policy,str) and policy in ("hold","unpowered"): action=np.zeros(3)
            elif policy=="random": action=action_rng.uniform(-1,1,3)
            elif policy=="ik": action=np.clip((env.ik(env.goal)-env.home)/env.command_span,-1,1)
            else: action=policy.predict(obs,deterministic=True)[0]
            obs,reward,terminated,truncated,info = env.step(action)
            cumulative += reward
            if record and episode==0 and step%3==0: frames.append(Image.fromarray(env.render()))
            if terminated or truncated: break
        episodes.append({"seed":seed,"return":round(cumulative,3),**info,"diagnostics":env.diagnostics()})
        if record and episode==0:
            Image.fromarray(env.render()).save(directory/"policy_final.png")
    if frames:
        frames[0].save(directory/"policy_rollout.gif",save_all=True,append_images=frames[1:],duration=60,loop=0)
    reasons = {}
    for e in episodes: reasons[e["termination_reason"]]=reasons.get(e["termination_reason"],0)+1
    return {"episodes":len(episodes),"successes":sum(e["is_success"] for e in episodes),
        "success_rate":sum(e["is_success"] for e in episodes)/len(episodes),
        "mean_final_error_mm":round(float(np.mean([e["error_mm"] for e in episodes])),3),
        "mean_return":round(float(np.mean([e["return"] for e in episodes])),3),
        "termination_reasons":reasons,"episode_results":episodes}


def train_simulation(root: Path,steps=65536,seed=7,evaluation_episodes=24):
    """Train one state-vector PPO experiment; compare held-out seeds to three baselines."""
    if not 1024<=steps<=2000000: raise ValueError("steps must be 1024-2000000")
    if not 0<=seed<=1000000 or not 4<=evaluation_episodes<=100: raise ValueError("Invalid seed or evaluation count")
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.monitor import Monitor
    torch.set_num_threads(1)
    source_before = source_digest(root)
    run_id = "reach-"+uuid.uuid4().hex[:16]
    directory = run_directory(root,run_id)
    directory.mkdir(parents=True,exist_ok=False)
    started = time.perf_counter()
    raw = WristReachEnv(root)
    snapshot = (raw.p,raw.cfg,raw.reference)
    readiness_snapshot = physical_readiness(root)
    if source_digest(root)!=source_before: raise ValueError("Source changed while snapshotting simulation inputs. Retry with stable source.")
    (directory/"scene.xml").write_text(raw.xml,encoding="utf-8")
    write_json(directory/"simulation.json",raw.cfg)
    write_json(directory/"hardware_reference.json",raw.reference)
    write_json(directory/"parameters.json",raw.p.model_dump())
    raw.reset(seed=seed)
    Image.fromarray(raw.render()).save(directory/"scene.png")
    raw.close()
    training = []
    class Progress(BaseCallback):
        def _on_step(self):
            for info in self.locals["infos"]:
                if "episode" in info:
                    training.append({"steps":self.num_timesteps,"return":float(info["episode"]["r"]),
                        "length":int(info["episode"]["l"]),"success":bool(info.get("is_success")),
                        "error_mm":info.get("error_mm"),"reason":info.get("termination_reason")})
            if self.num_timesteps%4096==0:
                write_json(directory/"progress.json",{"run_id":run_id,"status":"training","steps":self.num_timesteps,"requested_steps":steps})
                print(f"PPO training {self.num_timesteps}/{steps} steps",file=__import__("sys").stderr,flush=True)
            return True
    env = Monitor(WristReachEnv(root,snapshot))
    agent = PPO("MlpPolicy",env,device="cpu",seed=seed,n_steps=1024,batch_size=64,
        learning_rate=3e-4,gamma=.98,gae_lambda=.95,n_epochs=10,
        policy_kwargs={"net_arch":[64,64]},verbose=0)
    try:
        agent.learn(total_timesteps=steps,callback=Progress())
        agent.save(directory/"policy")
        write_json(directory/"training.json",training)
        heldout = list(range(seed+100000,seed+100000+evaluation_episodes))
        evaluation = WristReachEnv(root,snapshot)
        try:
            comparisons = {name:evaluate(evaluation,name,heldout) for name in ("unpowered","hold","random","ik")}
            comparisons["ppo"] = evaluate(evaluation,agent,heldout,directory,record=True)
        finally: evaluation.close()
        changed = source_digest(root)!=source_before
        report = {"schema_version":1,"run_id":run_id,"status":"completed","task":raw.cfg["task"],
            "created_at_utc":datetime.now(timezone.utc).isoformat(),"source_sha256":source_before,
            "stale_source":changed,"source_changed_during_run":changed,"training_seed":seed,
            "requested_training_steps":steps,"actual_training_steps":agent.num_timesteps,
            "evaluation_seeds":heldout,"wall_seconds":round(time.perf_counter()-started,2),
            "dependencies":{n:importlib.metadata.version(n) for n in ("mujoco","gymnasium","stable-baselines3","torch")},
            "units":{"length":"m (error mm)","mass":"kg","time":"s","angle":"rad","torque":"N m","contact_force":"N"},
            "criteria":{"position_tolerance_mm":raw.cfg["target_tolerance_mm"],
                "hold_seconds":raw.cfg["hold_actions"]*raw.cfg["physics_steps_per_action"]*raw.cfg["timestep_s"],
                "joint_speed_during_hold_rad_s":.5,"unexpected_contact_force_limit_n":raw.cfg["unexpected_contact_force_limit_n"]},
            "scope":raw.cfg["scope"],"assumptions":raw.cfg["physical_measurement_status"],
            "randomization":raw.cfg["randomization"],"comparisons":comparisons,
            "reward_policy":"exp(-25*error_m)-1 + 10*progress_m - 0.01*action_squared; success +8; failure -100",
            "physical_readiness":readiness_snapshot,
            "claim":"One trained seed and a small held-out simulation sample. Completion is not task or hardware qualification.",
            "artifacts":[]}
        write_json(directory/"progress.json",{"run_id":run_id,"status":"completed","steps":agent.num_timesteps})
        report["artifacts"] = [{"name":p.name,"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(directory.iterdir()) if p.is_file() and p.name!="report.json"]
        write_json(directory/"report.json",report)
        if not report["stale_source"]: write_json(directory.parent/"latest.json",{"run_id":run_id})
        return {key:report[key] for key in ("run_id","status","stale_source","actual_training_steps","wall_seconds","criteria","claim")} | {
            "comparisons":{name:{k:v for k,v in result.items() if k!="episode_results"} for name,result in comparisons.items()},
            "artifact_directory":directory.relative_to(root).as_posix()}
    finally: env.close()
