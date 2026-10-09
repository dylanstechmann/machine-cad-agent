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
