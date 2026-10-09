# Simulation before fabrication

Personal hobby and learning project developed with AI assistance. The aim is
to let agents perform most design, simulation, policy learning and analysis in
the computer, then use measured interfaces to make physical assembly repeatable.

## Running implementation

The pinned open source stack is MuJoCo 3.15.0, Gymnasium 1.4.0 and
Stable-Baselines3 2.9.0 PPO with CPU PyTorch 2.9.1. The Docker runtime includes
OSMesa for headless images. Training uses state observations and no rendering;
images and a GIF are recorded for evaluation.

```powershell
.\run.ps1 sim-train --steps 65536 --seed 7 --evaluation-episodes 24
.\run.ps1 sim-inspect
.\run.ps1 hardware
```

Use `./run.sh` on a compatible Docker host. The CLI permits longer experiments
up to two million steps. The viewer's **Physics & learning** link opens
`http://127.0.0.1:8765/simulation`. The training command does not start the
viewer; use `docker compose up -d viewer` if needed.

The implemented task is **local wrist reach and hold with a supported base**.
Three shoulder/elbow motors act on an articulated arm under gravity. Commands
pass through velocity-limited setpoints and a PD controller with finite torque.
Only episode reset sets joint positions directly. `mj_step` advances motion.
The initial pose is the IK solution for the center of a small target region,
with joint noise. This does not learn a full station approach or manipulation.
Observations use simulator joint state and an exact target position. Camera
perception, encoder noise, target estimation and sensor calibration are future
work; the trained policy currently depends on that simulated state interface.

Evaluation seeds are disjoint from the training seed. Each controller gets
the same target, mass, inertia, damping, torque and latency randomization for
each evaluation seed:

| Controller | Meaning |
| --- | --- |
| Motors off | Zero motor torque; gravity remains active |
| Powered home hold | Zero normalized command, holding the initial home setpoint |
| Random commands | Bounded independent random setpoints |
| Analytic IK setpoint | Geometric target angles with the same PD controller; no gravity feedforward |
| PPO | Learned state-to-command policy, evaluated deterministically |

Success requires the reported position tolerance held for the reported duration,
low joint speed, and no fatal force/speed/range/state warning. Time limits are
truncations. Contact forces and actual joint efforts are inspected at every
physics substep. Reports include saturation, contact pairs, peak force/speed,
termination reasons and solver warnings. A small final position error without
the hold criterion can still be a failed episode.

`configs/simulation.json` declares all assumed masses, inertia inputs, gains,
torques, target region and uncertainty ranges. Friction is randomized but does
not prove grasp robustness in a task which usually makes no contact. One
training seed and 24 evaluation episodes are preliminary evidence. Repeat
training seeds and expand target/domain coverage before claiming robustness.

Generated `builds/simulation/reach-*/` contains scene XML, frozen input profiles,
policy ZIP, episode returns, per-controller results, PNGs, replay GIF and a
manifest. Every environment in a run uses one input snapshot. Source drift is
recorded permanently; changed source marks historical experiments stale.
Requested PNG/GIF/policy artifacts are checked against their recorded hashes.
Saved policies come from this local training operation; no arbitrary downloaded
policy is executed by the tools.

MCP tools expose `get_hardware_reference`, `train_reach_policy`,
`get_simulation_report`, and `render_simulation`. MCP training is bounded to
32,768 steps to fit the tool time budget. Use the CLI for longer runs. A fresh
MCP session discovers the new tools.

## Product evidence

The supplied NIJ/Temu screenshot advertises **78 mm outside diameter and
254.8 mm overall height**. Simulation uses this exterior as a stationary solid
obstacle. The usable cavity, fill mark, opening plane, base/lid split, threads,
mass and cap torque remain unknown. The generic CAD storyboard's approximately
658 mL cavity and 500 mL recipe do not establish compatibility with that blender.

The supplied Perplexity text contains reseller leads, rather than verified
engineering specifications. The retrieved
[eBay listing](https://www.ebay.com/itm/406211052306) uses Net Clouder in its item
specifics. It does not establish the supplied unit's internal geometry or an
official blueprint. Battery capacity and exact relist matching remain unverified.
Keep these leads in the hardware profile without turning them into dimensions.

The owner selected **Orgain Vanilla Bean**, with **Creamy Chocolate Fudge** as
an alternative, excluding the peanut butter reference image. The
[manufacturer's vanilla product page](https://orgain.com/products/organic-protein-plant-based-protein-powder-vanilla-bean)
specifies two scoops; its how-to section lists 8–12 US fl oz liquid and its FAQ
lists 12–16. The
[official product catalog](https://healthcare.orgain.com/media/rdocs/Orgain_HCPCatalog_Oct24.pdf)
lists two scoops / 46 g for Vanilla Bean. These are label references, not a
calibration of our 30 mL hemispherical scoop. Package/formulation, scoop mass,
bulk density, actual tub dimensions and cap interfaces need measurement.

`configs/hardware_reference.json` keeps facts, sources, owner preferences and
null measurements separate from simulation assumptions and nominal CAD inputs.

## Next curriculum and engineering dependencies

| Stage | Current status | Evidence needed before advancing |
| --- | --- | --- |
| Supported local wrist reach | Implemented physics and PPO experiment | Broader targets, more training seeds, observed motor limits and inertia |
| Wrist orientation and gripper | Planned | Relative wrist joint mapping, travel limits, transmission and torque/mass |
| Grip and lift a rigid surrogate | Planned | Contact forces, slip/drop rates, payload and pad friction sweeps |
| Open/reseat cap | Planned | Measured cap and fixture geometry; twist/axial coupling and reaction torque |
| Scoop and water transfer | Kinematic storyboard only | Calibrated scoop/dispense model and explicit spill/dose criteria |
| Standing and walking | Kinematic storyboard only | Lateral hip/ankle mechanics, support contacts, balance and whole-body control |
| Printing and assembly release | Pending | Selected actuators/materials/fasteners, structural loads, tolerances and measured fits |

An LLM/VLM can edit CAD and environment code, inspect failure states, select
curriculum parameters, invoke training, compare policies and produce revisions.
RL supplies learned motor behavior within each defined task. Use separately
reviewable skills and deterministic recipe/limit logic to coordinate the task.
A reward score is not evidence that the entire robot can prepare a shake.

The present multiple-turn cap storyboard also needs a continuous rotary drive
or an explicit regrasp strategy. World-oriented tools require relative wrist
rotation, and world-level feet need actual ankle mechanics. These mechanisms
are still design work.

## Making fabrication quicker

Develop modular printed subassemblies around purchased actuators, bearings,
shafts and fasteners. Preserve original blender food-contact parts and its
motor/blade assembly. Initial printing candidates are the character shell,
link brackets, mounting adapters and fixtures; the current solids are studies.

Before finalizing those parts:

1. Capture exterior/mating dimensions and unobstructed photos with a ruler.
   Record actual permitted fill and empty/filled mass; keep unknowns explicit.
2. Measure the Orgain tub, cap and scoop. Repeat level-scoop mass measurements
   and report spread rather than treating nominal scoop volume as exact dosing.
3. Select actuator candidates using measured loads plus simulated effort, speed,
   thermal/current and transmission requirements. Simulation currently has no
   purchased motor's torque-speed curve, backlash or thermal model.
4. Develop screw/bearing interfaces, tolerances, cable routing and fixtures.
   Print small fit coupons before full links. Add structural analysis with the
   selected material/process and fastener loads.
5. Export a versioned assembly packet: measured interface drawings, approved
   material/process, part orientation, BOM, fasteners and assembly order.

Physics can find many problems cheaply. It cannot infer missing cap dimensions,
friction, stiffness, motor behavior or powder flow from a product photo. A small
amount of calibration and staged physical checks will still be needed.

## Software references

- [MuJoCo Python](https://mujoco.readthedocs.io/en/stable/python.html)
- [MuJoCo collision computation](https://mujoco.readthedocs.io/en/stable/computation/index.html)
- [MuJoCo fluid-model limits](https://mujoco.readthedocs.io/en/stable/computation/fluid.html)
- [Stable-Baselines3 PPO](https://stable-baselines3.readthedocs.io/en/v2.9.0/modules/ppo.html)
- [Gymnasium environment interface](https://gymnasium.farama.org/api/env/)

MuJoCo's mesh collisions use convex hulls: future hollow cups need compound
walls or an intentional alternative collision model. Its fluid-force models
do not simulate a liquid free surface, powder dosing, mixing or spills.
