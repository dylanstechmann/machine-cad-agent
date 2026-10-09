# Machine CAD Agent

Open source mechanical CAD that an LLM can edit, rebuild, measure, inspect with a
VLM, and export through Python and MCP. A personal hobby and learning project,
developed with AI assistance.

## Meet Pocket Pal

The example is an original **Game Boy Color inspired robot character** with a
purple console shell, expressive screen, speaker envelope, articulated legs,
two arms and parallel grippers. The source produces solid CAD and a complete
kinematic storyboard for preparing a vegan protein shake:

1. Walk to a low preparation station and introduce itself.
2. Unscrew the protein container cap and park it.
3. Open a portable battery-powered blender and pour an initial water portion.
4. Measure and transfer **two or three scoops** with an angled dip and bowl-centered tip.
5. Top up water while reserving headspace.
6. Retrieve the blender cap, follow a nominal helical thread path, and apply a
   proposed torque feedback policy.
7. Leave the power button to an independent human, who blends, drinks and
   thanks Pocket Pal. Optional browser speech supplies the robot's voice.

![Generated Pocket Pal CAD view](docs/preview.png)

**This is a running digital concept.** No physical robot, motor controller,
fluid simulation or calibrated purchased blender is connected. Walking is
leg kinematics; balance and dynamics remain to be developed. The grippers and
held objects move with explicit transforms, and arm reach is solved numerically.
The cap profiles and torque limits are nominal inputs. They do not establish
that a real cap will be tight, undamaged or easy to reopen.

## Run it

Prerequisite: Docker with Compose v2 running. The pinned CadQuery runtime uses
Open CASCADE for solid modeling. No paid CAD application or host Python is needed.

```powershell
.\run.ps1
```

On macOS/Linux, use `./run.sh`. This builds the runtime, generates a
`pass / fail / pass` example, and starts **http://127.0.0.1:8765**.
The fault intentionally requests 700 mL in a roughly 658 mL cup. Its report and
previews remain available, while STEP/STL exports are withheld. This is a
deterministic pipeline exercise, not an autonomous engineering benchmark.

The viewer provides an orbitable scene, play/pause and a pose slider, recipe
state, optional voice, a simulated human handoff, diagnostic revisions and
downloads. It is local to your computer and controls no hardware.

```powershell
.\run.ps1 test          # Geometry, STEP and real stdio MCP checks
.\run.ps1 build         # Canonical robot build
.\run.ps1 parameters    # Defaults and strict override schema
.\run.ps1 stop          # Stop the local viewer
```

Source and config are mounted into the container. Python edits take effect on
the next build. Rebuild the image after changing dependencies. Generated files
belong in ignored `builds/`.

## Give the AI a large role

The CAD source is the editable design. The agent can change part geometry,
dimensions, poses and check logic, then obtain numerical and visual feedback.
MCP exposes the same reproducible operations used by the CLI and CI.

```powershell
.\scripts\register-codex.ps1
```

Start a fresh Codex session in this trusted project to load `machine_cad_agent`.
The script registers this checkout's Docker stdio server and supplies 30-second
startup and 180-second tool timeouts when unset. The server needs no API key;
the client supplies the LLM/VLM. Other MCP clients can launch:

```text
docker compose --project-directory /absolute/path/to/machine-cad-agent -f /absolute/path/to/machine-cad-agent/compose.yaml run --rm -T dev python -m machine_cad.mcp_server
```

| Tool | Feedback |
| --- | --- |
| `get_parameters` | Defaults and permitted overrides: mm, mL, N m |
| `check_model` | Solid, kinematic, recipe and selected collision checks |
| `build_model` | Rebuild CAD, motion scenes, views, reports and gated exports |
| `inspect_model` | Full report, scope, source/input provenance and file hashes |
| `measure_part` | Actual solid bounds, volume and placement |
| `render_views` | Native PNG images for VLM inspection |
| `get_sequence` | Paged tool poses, held objects, fill states and cap paths |
| `get_motion_report` | Paged interval checks, sampling policy, spacing and failures |
| `render_motion_failure` | Native PNG of a failing intermediate sample, when reachable |
| `export_files` | STEP/STL/BOM paths for a fresh passing build |

Example agent task:

> Make a trial using two scoops. Read the recipe and motion report, inspect the
> robot front and scoop-transfer images, and list exports if the digital checks
> pass. Leave the canonical configuration unchanged until the trial is reviewed.

Use `get_motion_report` to inspect the intermediate route. When an interval
fails, its report names the source/destination poses, sample fraction and
overlapping parts. `render_motion_failure` supplies a native diagnostic image.
Both paged tools return a next-page index to keep agent feedback manageable.

Overrides affect only that build. Persistent edits go in `configs/pocket_pal.json`
or Python. A source/config change makes previous outputs stale. Follow
[AGENTS.md](AGENTS.md) for revision discipline.

## What is implemented

- 59 named physical component studies, plus separate volume illustrations.
- Hollow shell, faceplate, screen, controls and speaker/battery packaging.
- Two-link arms with analytic IK/FK, explicit world tool orientation, staggered
  hinge plates and translating jaws. Wrist orientation represents a future
  three-axis gimbal; motor selection and detailed transmission are outstanding.
- Two-link sagittal leg poses and planted/swing feet.
- Intermediate geometric sampling, with fresh IK/FK at each sample. Thread yaw
  retains its winding, a tipped scoop keeps its bowl over the cup, and grasp,
  release and recipe events remain discrete.
- Protein jar, measured hemispherical scoop, water carafe, portable-blender
  envelopes, cap parking pads and fixture packaging.
- Default recipe: 200 mL initial water, 3 × 30 mL nominal scoop volume, 210 mL
  top-up, 500 mL fill and about 158 mL geometric headspace. Powder displacement
  is a conservative recipe input, not a mass or dissolution measurement.
- Nominal cap rotation coupled to axial thread pitch. A pure feedback function
  stops at the proposed seated torque target, or faults at the hard stop,
  excessive axial error or invalid feedback. It drives no actuator.
- Six PNG/SVG views, a GLB per key pose, assembly and individual STEP files,
  printable/fixture-study STL files, CSV BOM and JSON recipe/motion/report data.
- A separate `trajectory.json` records interval counts, observed spacing,
  collision evidence, sampling limits and build/source provenance. Up to four
  failing intermediate poses receive diagnostic PNG/GLB previews.
- Digital checks and a failure export gate, exercised through real MCP stdio.

STEP files can be edited or inspected in open source FreeCAD or another CAD
application. CadQuery is the primary automation layer; Blender remains useful
for presentation. The character uses original geometry without copied games
or brand artwork.

## Source and evidence

| File | Role |
| --- | --- |
| `model.py` | Named solid geometry and rigid placements |
| `kinematics.py` | Arm IK/FK, leg solving and tool transforms |
| `sequence.py` | Task states, recipe accounting, cap path and torque policy |
| `trajectory.py` | Interpolation, discrete ownership/events and sample subdivision |
| `collisions.py` | Conservative box pruning and cached exact intersection volumes |
| `validation.py` | Bounded digital checks and explicit failure details |
| `pipeline.py` | Export gate, previews and build provenance |
| `mcp_server.py` | Agent tools with structured results and native images |
| `web/` | Local artifact viewer and browser handoff simulation |
| `tests/` | Digital geometry and protocol checks |

Passing means the **listed checks** passed. Key poses and sampled intermediate
poses check limbs against the body/station/objects, objects against the
body/station/other objects, and the body against the worktop. Foot clearance,
held transforms and recipe bounds are also checked. Internal robot
self-collisions and intentional mounting interfaces are excluded.
Finite sampling does not certify continuous or all-pairs collision freedom.
Purchased fit, clamping forces,
strength, food-contact materials, dosing, spill handling, sensors, motor drive,
walking balance and physical cap torque require further engineering.

[Validation record](docs/VALIDATION.md) distinguishes agent-run evidence from
physical development. GitHub CI builds the pinned runtime, runs the tests and
the overfill demo, and retains artifacts for seven days. Build IDs identify
effective parameters, source and dependency versions; serialization timestamps
are not promised to be byte-identical.

The sampling policy uses at least four subdivisions per interval, with more
for translation, rotation and jaw travel. Its 20 mm translation allowance,
15 degree angle target and 5 mm jaw target guide subdivision; the report also
gives observed tool spacing. These are not bounds on all IK link sweeps. If
the 4,096-interior-sample budget is exhausted or an ownership transition is
undefined, the report is incomplete and fabrication exports are withheld.
Source changes during inspection/generation also prevent publication of a
passing revision. Direct viewer STEP/STL URLs enforce freshness and passing
status, alongside the MCP export gate.

## Credits

[CadQuery](https://cadquery.readthedocs.io/en/stable/) and Open CASCADE,
[MCP Python SDK](https://py.sdk.modelcontextprotocol.io/),
[CairoSVG](https://cairosvg.org/), Google's
[model-viewer](https://modelviewer.dev/) and
[Codex MCP documentation](https://developers.openai.com/codex/mcp/).
The viewer's bundled license and source metadata are in `web/vendor/`.
Project source is MIT licensed; dependencies retain their licenses.
