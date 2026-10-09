# Pocket Pal validation record

Digital checks are executed by an AI coding agent in the pinned Docker runtime.
They are not physical trials or tests personally performed by the owner.

## Initial key-pose release, 2026-10-09

This earlier record applies to commit `6bef3d5` before intermediate-path checking.

- The 14 automated geometry/STEP/MCP tests passed in the pinned Docker runtime.
- The overfill demo produced `pass / fail / pass`, with the failing revision
  withholding fabrication exports.
- The local browser displayed the colored character and station. Its final
  handoff showed 500 mL fill, 158 mL rounded headspace and three scoops. The
  human-only blend, drink and thank-you controls progressed in order and
  Pocket Pal replied “You're welcome.” Voice was left off during inspection.
- A separate Codex session used the registered MCP tools to build a two-scoop
  trial, inspect its report and sequence, measure the shell, visually inspect
  native front/scoop-transfer PNGs, and retrieve passing exports. It calculated
  240 mL top-up and left the three-scoop baseline unchanged. This is one agent
  tool-use example, rather than a benchmark of autonomous machine design.

## Sampled-path development, 2026-10-09

The expanded geometry checks found interference in the previous resting hands,
table/hip clearance, cap parking pads, scoop support, and some hand/tool paths.
The coding agent revised the station edge, supports, shoulder standoff,
connected gripper fingers, empty-hand approaches/withdrawals, carafe tilt
waypoints and scoop orientation.

The revised three-scoop route passed **147 key poses plus 1,192 interior
samples**, across 146 intervals. The numeric operation took about 30 seconds
in the local pinned Docker runtime. The largest observed tool-point gap was
20 mm and Euler-command gap about 7.557 degrees. These are observed sample
spacings, not a continuous collision certificate. The recipe remains 500 mL
with about 158 mL headspace.

Geometric samples are separate from display poses. Body/feet/tool targets are
interpolated and IK is solved again, rather than interpolating already drawn
links. A held scoop interpolates its world bowl center. Thread intervals keep
unwrapped yaw; ordinary gimbal commands take nearest equivalent Euler angles.
Pickup occurs at the destination, release at the source, and recipe events
are applied only at their key poses. Undefined handoffs/free-object movement
produce incomplete or failed evidence. The sampling budget is never silently
clamped into a passing report.

A fresh SDK MCP session discovered all ten tools. A deliberately reduced
65 mm shoulder standoff produced a failed candidate with 27 failing intervals.
The paginated motion report identified an intermediate upper-arm/faceplate
overlap, and the native-image tool returned its PNG for visual inspection.
Fabrication export was refused. The local viewer also opened that sample at
50% of its interval, showed the overlapping parts and kept human controls
disabled. The passing baseline was then restored as the default viewer build.
No additional automated tests were added or run locally for this revision.

## Checked scope

- Valid single-solid named components and actual bounds/volumes.
- Shell STEP reimport and measured blender cavity volume.
- Every listed arm target reachable with FK matching its TCP; leg link lengths
  and nonnegative foot clearance.
- Held-object transforms and scoop bowl centering over the cup.
- Cap rotation/axial pitch accounting and a pure torque feedback policy.
- Recipe headspace, supply, scoop count and open-vessel preconditions.
- B-rep intersections at key and sampled intermediate poses: limbs versus
  body/station/objects, objects versus body/station/other objects, and body
  versus worktop. Internal robot self-interference/mounting interfaces are
  excluded. Conservative bounding boxes prune separated pairs; exact cached
  intersection volumes reject overlap greater than 0.001 mm³.
- Representative nonintersecting staggered arm/leg hinges and seated cap contact.
- Human-only blender power and final handoff.
- Real MCP discovery, rebuild, measurements, native images, sequence data,
  passing exports and refusal of failed exports or invalid input.

The default recipe uses 200 mL water, three nominal 30 mL scoops and 210 mL
water top-up. The 657.787 mL modeled cavity leaves 157.787 mL headspace at
500 mL fill. Two scoops instead require 240 mL top-up.

The deterministic demo requests 700 mL to demonstrate a headspace failure and
withheld STEP/STL output, then restores the default recipe.

## Supported-arm physics and learning, 2026-10-09

The coding agent built the pinned MuJoCo/Gymnasium/CPU PyTorch/PPO runtime and
ran experiment `reach-ddce9b1271d042cc`: 65,536 training steps, seed 7, and 24
separate evaluation seeds. The local operation took about 461 seconds. It used
the frozen source SHA256
`cea728e9e575dbafcdce80473ccbd6691c5eed6566a482f55a0d273a200d9fb7`.

Success was an 8 mm wrist-position tolerance held for 0.30 seconds, with low
joint speed and no fatal state/speed/range/contact warning. Results:

| Controller | Successes / 24 | Mean final error |
| --- | --- | --- |
| Motors off | 0 | 75.564 mm |
| Powered home hold | 1 | 29.192 mm |
| Random commands | 0 | 33.366 mm |
| Analytic IK setpoint + same PD | 23 | 3.444 mm |
| Learned PPO | 13 | 3.940 mm |

PPO improved on hold/random commands but did not match the analytic controller's
success rate. Eleven PPO episodes timed out; a low final error is insufficient
without the stable hold criterion. No PPO episode terminated for fatal contact
in this sample. This is preliminary evidence for a local reaching skill, not
proof of full-task autonomy or robust physical control.

A fresh MCP SDK session discovered all 14 tools, read the Vanilla Bean hardware
profile, invoked a separate 1,024-step PPO experiment, read controller results
and returned a native physics PNG which the agent viewed. Its PPO had 0/4
successes and its IK baseline 4/4. CAD study export remained available with
`manufacturing_release: false`. The rebuilt nominal CAD study passed its
1,339 poses and included the new hardware readiness metadata. No additional
automated tests were added or run locally for this revision.

The renderer uses primitive collision/visual envelopes and a supported base.
Mass, torque, friction and control-delay distributions are assumptions, not
measured purchased components. See [simulation scope and plan](SIMULATION.md).

## Physical work outstanding

Continuous trajectory collision freedom and all-pairs interference are not
qualified. No balancing controller, drivetrain, fabricated gimbal, sensors,
gripper force control, vendor threads, measured cap damage/reopening torques,
calibrated powder dosing or fluid dynamics are implemented. The fixture rings
are packaging envelopes with clearance; actual clamps must be developed to
react cap torque. Printable studies require manufacturing development.

Run `.\run.ps1 test` or `./run.sh test`, followed by the demo, to reproduce the
digital evidence. Machine-specific artifacts and protocol logs remain in
ignored `builds/`. A passing build does not authorize physical operation.
