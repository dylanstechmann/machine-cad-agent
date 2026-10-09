# Pocket Pal humanoid engineering references

Research checked October 9, 2026. Initial hardware budget: **under US$1,000**,
excluding borrowed printers, tools and computers. Preparing the protein shake
with functional hands takes priority. The long-term body remains a humanoid
with arms, legs, feet and a flexible torso beneath the console character.

This is a recommendation and source map. The donor mechanisms have not been
integrated into Pocket Pal. Its current CAD hands are geometric poses, and its
physics task is supported three-joint arm reaching. None of these references
establishes general human-equivalent capability or a complete autonomous
shake-making humanoid within the initial budget.

## Recommended direction

Develop the complete skeleton digitally and spend the first hardware budget
on **one real hand, a supported wrist, grippy pads and an instrumented cap
fixture**. Extend that module into an arm and supported two-arm torso before
funding the biped. Each purchased subassembly should advance the actual task.

Evaluate Aero Hand Open first as a five-digit simulation candidate, at its
original scale. A physical build requires fresh component quotes and acceptance
of its noncommercial hardware terms. AmazingHand offers more permissive
mechanical licensing, but has four digits; adding a fifth is a new design task.
Study ToddlerBot's arms and legs, Berkeley's printed actuators, Poppy's torso
and Asimov's passive toes. These are engineering references, not interchangeable
parts or a proven combined robot.

## Hands, thumbs, fingers and grip

| Reference | Actual resources | Cost and practical boundary |
| --- | --- | --- |
| [Aero Hand Open](https://github.com/Chestnut-Robotics/aero-hand-open) | Five digits, seven actuators, sixteen joints; STEP, print files, BOM, PCB, firmware, Python/ROS2, MuJoCo and RL. | README advertises US$314, but the [linked live store](https://shop.tetheria.ai/) says it no longer sells Aero Hand Open. Treat it as a self-sourced design requiring new quotes, not an available $314 kit. |
| [Pollen AmazingHand](https://github.com/pollen-robotics/AmazingHand) | Four digits, eight motors, linked phalanges, flexible shells, STEP/STL and assembly/control demos. | Original authors' estimate: under EUR200 plus chosen control interface. [Enhanced](https://github.com/pollen-robotics/AmazingHand/tree/Amazing-Hand-Enhanced/AmazingHand_Enhanced) uses different servos and costs more. Original price does not describe Enhanced. |
| [InMoov](https://inmoov.fr/download/) | Printable hand, wrist, forearm, biceps, shoulders and torso; tendon routing and [assembly guidance](https://inmoov.fr/assembly-help/). | Useful life-size construction reference; current complete functioning arm cost and task payload not verified. |
| [Yale OpenHand](https://www.eng.yale.edu/grablab/openhand/) | Source CAD and compliant finger molding/assembly. [Model O](https://www.eng.yale.edu/grablab/openhand/model_o.html) has three fingers/four motors. | Excellent grip-mechanism reference, but not five-digit anatomy. Holding-force specifications do not establish cap-opening torque. |

Aero's useful starting files are its [hardware folder](https://github.com/Chestnut-Robotics/aero-hand-open/tree/main/hardware),
[BOM](https://github.com/Chestnut-Robotics/aero-hand-open/blob/main/hardware/Assembly/BOM.csv),
[mechanical specification](https://docs.tetheria.ai/docs/mechanical_overview/),
[simulation guide](https://docs.tetheria.ai/docs/hand_sim/),
[MuJoCo models](https://github.com/google-deepmind/mujoco_menagerie/tree/main/tetheria_aero_hand_open)
and [Playground task code](https://github.com/google-deepmind/mujoco_playground/tree/main/mujoco_playground/_src/manipulation/aero_hand).
The documented hand is about 198 x 95 x 53.5 mm and under 400 g. Three active
thumb motions provide opposition and curl; the remaining fingers each use one
actuator driving coupled joints. Optional silicone contact pads are documented.
This hand is large relative to the current 410 mm Pocket Pal. Size the body
around real mechanisms; shrinking meshes does not preserve actuator fit,
strength or payload.

AmazingHand provides [CAD](https://github.com/pollen-robotics/AmazingHand/tree/main/cad)
and an [assembly PDF](https://raw.githubusercontent.com/pollen-robotics/AmazingHand/main/docs/AmazingHand_Assembly.pdf).
Its authors say prolonged complex grasping has not been validated. Neither
hand establishes the exact Orgain/NIJ workflow. The newer high-DOF products on
Chestnut's current website are not the seven-actuator Aero Hand Open design.

For later funding, [LEAP v1](https://v1.leaphand.com/) and
[LEAP v2 Advanced](https://v2-adv.leaphand.com/) offer detailed manipulation
research, but published costs of approximately $2,000 and $3,000 exceed the
initial budget. The separate inexpensive v2 demonstration is not Advanced.

## Bodies, shoulders, arms, hips and legs

| Reference | Usable engineering artifacts | Important boundary |
| --- | --- | --- |
| [ToddlerBot](https://toddlerbot.github.io/) | [CAD](https://cad.onshape.com/documents/565bc33af293a651f66e88d2), [BOM](https://hshi74.github.io/toddlerbot/hardware/01_bill_of_materials.html), [assembly](https://hshi74.github.io/toddlerbot/hardware/04_assembly_manual.html), [control/RL](https://github.com/hshi74/toddlerbot). Real walking and manipulation demonstrations. | Original [paper](https://arxiv.org/html/2502.00893v3): about 0.56 m, 3.4 kg and $6,000 BOM. Thirty body actuators, excluding added end effectors. Large hands and human-sized containers change load assumptions. |
| [Original Berkeley Humanoid Lite](https://lite.berkeley-humanoid.org/) | [CAD/actuator releases](https://berkeley-humanoid-lite.gitbook.io/docs/releases), [BOM](https://berkeley-humanoid-lite.gitbook.io/docs/getting-started-with-hardware/materials-and-parts-bom), [URDF/MJCF/USD and joint list](https://github.com/HybridRobotics/berkeley-humanoid-lite-assets), [training/deployment](https://github.com/HybridRobotics/Berkeley-Humanoid-Lite). Printed cycloidal joints and demonstrated locomotion. | Original [paper](https://arxiv.org/html/2504.17249v1): 0.8 m, 16 kg, US BOM $4,312. Five arm axes and six leg axes per side; grippers extra. Wrist/waist development needed for our morphology. |
| [HOPEJr](https://github.com/TheRobotStudio/HOPEJr) | [Arm/hand build](https://github.com/TheRobotStudio/HOPEJr/tree/main/Arm), [STEP](https://github.com/TheRobotStudio/HOPEJr/tree/main/Arm/STEP), [LeRobot](https://huggingface.co/docs/lerobot/hope_jr). Seven arm motors plus sixteen hand motors. | Recording/training is experimental. Complete ready-to-build walking at the $3,000 headline was not verified; latest Arm license is unresolved in [issue #6](https://github.com/TheRobotStudio/HOPEJr/issues/6). |
| [Poppy Humanoid](https://github.com/poppy-project/poppy-humanoid) | [SolidWorks/STEP/STL releases](https://github.com/poppy-project/poppy-humanoid/releases), BOM and articulated torso. | Published full-build estimate $8,000-9,000. Default four-axis arms and five-axis legs differ from our target. |

ToddlerBot's [current body MJCF](https://github.com/hshi74/toddlerbot/blob/main/toddlerbot/descriptions/toddlerbot_2xc/toddlerbot_2xc.xml)
has seven actual arm pose actuators: three shoulder, two elbow/forearm and two
wrist axes. The count does not include a gripper. Its two waist axes are yaw
and roll, so forward bending would require a modification.

The newer [Berkeley arm](https://github.com/Berkeley-Humanoids/berkeley-humanoid-lite-arm)
and [Lite Description](https://github.com/berkeley-humanoids/lite_description)
are separate projects. The latter labels full-body variants model-only. Do
not transfer the original Lite's cost or walking evidence to those designs.
All published robot prices here are historical project BOM estimates, not
current delivered quotes including dexterous hands, spares and a new shell.

## Feet, toes and spine

[Asimov 0's structural guide](https://docs.menlo.ai/asimov/0/hardware/frame-and-structural-components)
contains a STEP download, exploded parts diagram and joint limits: six powered
axes per leg plus one passive toe joint per foot. See its
[joint mechanisms](https://docs.menlo.ai/asimov/0/hardware/joint-design-and-actuation)
and [CAD/model repository](https://github.com/menloresearch/asimov-v0).
The large actuators and industrial fabrication choices are references, not
a cheap drop-in lower body.

Poppy's [motor configuration](https://github.com/poppy-project/poppy-humanoid/blob/master/software/poppy_humanoid/configuration/poppy_humanoid.json)
lists five torso axes: abs_y, abs_x, abs_z, bust_y and bust_x.
[Roboy](https://roboy.org/core/) documents tendon-driven shoulders, a spine and
soft skin; [CARDSFlow](https://roboy.org/cardsflow/) explains its cable-robot
CAD/simulation workflow. Roboy notes that some CAD/team documentation needs
maintainer access. It is a biological-mechanism research reference rather than
a complete low-budget kit.

## Proposed Pocket Pal skeleton

These are design targets, not implemented joints or selected actuators:

| Subassembly | Powered motions | Purpose |
| --- | --- | --- |
| Each arm | 3 shoulder + elbow bend + forearm rotation + 2 wrist bend axes = 7 | Orient the hand while reaching around containers |
| Each hand | Five digits, about 7 actuators with coupled joints | Opposing thumb, power grip, pinch, scoop and release |
| Each leg | 3 hip + knee + 2 ankle = 6 | Support and eventual controlled walking |
| Waist | Turn and forward bend = 2 | Reach and posture; sideways bend optional later |
| Each foot | Passive forefoot hinge and replaceable sole | Toe-off without five toe motors |
| Face | Rigid display on chest plate | Console appearance without bending the screen |

The full proposal has approximately **42 powered axes** before a neck or other
accessories. This explains why all-new full-body hardware is outside the first
$1,000. A preliminary 0.55-0.8 m body range would use a low workbench; final size
must follow payload/torque and packaging studies. New hands, skin, link lengths
and masses require an updated dynamics model and policies.

Use stiff structural links with bearing/shaft interfaces and replaceable soft
contact surfaces. The [Yale finger fabrication guide](https://www.eng.yale.edu/grablab/openhand/OpenHand%20Finger%20Guide.pdf)
gives real molds and pin/flexure alternatives, including Vytaflex 30 pads and
PMC-780 flexures. The [ORCA paper](https://www.orcahand.com/publications/ORCA_IROS_2025.pdf)
documents printed structure and cast silicone fingertip skin over sensors.
It treats its under-skin FSR readings as binary contact, because skin/contact
position distort their force measurements.

Engineering recommendation: begin with removable silicone finger/palm pads,
rubber soles and accessible tendons. Compare dry, wet and powder-contaminated
grip. Add segmented TPU/silicone shell sections later, with folds or gaps at
moving joints. Continuous skin adds resistance and complicates cooling and
service. The screen can stay rigid on the chest; flexible-screen selection can
wait for a specific datasheet and supported electronics.

## First hardware stage: planning allocation

| Item | Ceiling (USD) |
| --- | ---: |
| One self-sourced five-digit hand, including servos/electronics | 400 |
| Supported wrist, bearings, axial slide/compliance and cup/tub fixture | 150 |
| Power, wiring, connectors and motor-disable hardware | 100 |
| Contact/load measurement and calibration items | 75 |
| Additional material, pads, fasteners and adapters | 75 |
| Tax, shipping, replacement parts and contingency | 150 |
| **Total allocation** | **950** |

These are spending limits for scoping, **not a verified shopping cart**.
Assume borrowed computer, camera, printer and tools. Re-price the complete hand
BOM; the retired kit price is not an available offer. If parts exceed their
allocation, borrow equipment or narrow the rig. Two arms, two hands and walking
legs need later funding. An arm's payload assessment must include the hand's
own mass; a compatible mounting plate is insufficient.

## Simulation before purchases

1. Pin a donor revision and file-level licenses. Import the original hand,
   preserving actual axes, tendon coupling and actuator limits. Check units,
   collisions and inertias against CAD.
2. Exercise a supported hand around a nominal 78 mm cup and parameterized
   large tub lid. Treat unmeasured mass, friction, thread pitch and torque as
   distributions. Use failed grasps to compare morphology.
3. Add a torque-limited wrist, passive axial compliance or a short linear
   slide, and anchored container. A screw cap rises with thread pitch; a
   rotation-only rigid mount would bind. Learn grasp, twist, release and
   regrasp; finite wrist travel must remain finite. Qualify grip and thread
   seating separately, initially with a helical constraint before more
   detailed thread contact.
4. Expand to two arms, scooping and a modeled dispenser. Scalar dose/fill
   bookkeeping does not simulate powder flow or liquid slosh.
5. Add balance and walking after supported manipulation. Randomize payload,
   sensor error, backlash, tendon slack, friction and delay; compare learned
   policies against simpler controllers on held-out conditions.

LLMs/VLMs can automate CAD/environment edits, builds, training jobs, failure
image inspection and experiment comparison through Python/MCP. Learned policies
and feedback controllers operate modeled motors. A language-model connection
alone does not supply human dexterity.

Success evidence should include completion, drops/spills, slip, seating and
reopening torque, current/temperature and repeatability. Thresholds remain
design inputs. Limited physical calibration of joints, tendons and contacts
will still be needed after simulation narrows the design.

## Preserve the actual reuse terms

| Source | Hardware/design | Software/model distinction |
| --- | --- | --- |
| [Aero license](https://github.com/Chestnut-Robotics/aero-hand-open/blob/main/LICENSE.md) | CC BY-NC-SA 4.0: CAD, drawings, BOM, docs | Firmware/SDK Apache-2.0. Separate Menagerie directory declares Apache-2.0; that does not relicense physical CAD. |
| [AmazingHand](https://github.com/pollen-robotics/AmazingHand#readme) | CC BY 4.0 | Code Apache-2.0 |
| [ToddlerBot](https://github.com/hshi74/toddlerbot#license) | CC BY-NC-SA 4.0 | Code MIT |
| [Original Berkeley assets](https://github.com/HybridRobotics/berkeley-humanoid-lite-assets) | CC BY-SA 4.0 | Main code MIT |
| [Poppy](https://github.com/poppy-project/poppy-humanoid) | CC BY-SA 4.0 | Software GPLv3 |
| [Asimov 0](https://github.com/menloresearch/asimov-v0) | CERN-OHL-S-2.0 | Check selected model/code files separately |
| [Yale hardware](https://github.com/grablab/openhand-hardware/blob/master/LICENSE.md) | CC BY-NC 3.0 | Separate control repository has its own license |
| [InMoov](https://inmoov.fr/download/) | Official site specifies CC BY-NC | Pin exact terms for selected files |
| [HOPEJr Arm](https://github.com/TheRobotStudio/HOPEJr/issues/6) | Latest Arm subtree terms unresolved | Humanoid subtree's Apache file does not establish Arm licensing |

Downloadable designs and unrestricted open hardware are different properties.
Keep attribution and licenses with future imported files; do not silently
relicense them as this project's MIT source. This research copied no donor
CAD or code into the repository.

## Student resources

The [FAU Engineering Fab Lab](https://www.fau.edu/engineering/fablab/) lists
[printers, machining and electronics equipment](https://www.fau.edu/engineering/fablab/gadgetry-materials-new/).
Access and consumable costs need confirmation. The separate
[Machine Shop](https://www.fau.edu/engineering/student-labs-shops/machine-shop/)
requires training/work requests and ties student eligibility to funded
research or class assignments.

[FAU OURI](https://www.fau.edu/ouri/undergraduate-grants/) currently lists a
September 1-October 15 window: October 15 is six days after this research date.
Its [linked January 2025 guide](https://www.fau.edu/ouri/undergraduate-grants/ugrg-programinfo-spring2025.pdf)
states up to $600 individually/$1,200 for groups, a faculty mentor and
undergraduate eligibility conditions. Confirm current-cycle amounts and
eligibility; purchased equipment remains university property.

[FAU COSO](https://www.fau.edu/involvement/clubhouse/coso/cosofunding/) describes
conditional emergency funding up to $1,000 per organization per semester.
[IEEE Student Branch resources](https://students.ieee.org/student-branch-resources-2/)
point to parent Section/Society support. A focused proposal could study how
fingertip compliance and visual feedback affect repeatable cap manipulation.

IEEE RAS's listed January/May 2026 chapter deadlines have passed.
[EPICS' October 2026 call](https://epics.ieee.org/october-2026-epics-in-ieee-call-for-proposals/)
requires an eligible community-service project and partner; a personal shake
robot alone does not establish eligibility. No applications, contacts or
purchases were made.
