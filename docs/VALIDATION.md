# Pocket Pal validation record

Digital checks are executed by an AI coding agent in the pinned Docker runtime.
They are not physical trials or tests personally performed by the owner.

## Agent-run record, 2026-10-09

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

## Checked scope

- Valid single-solid named components and actual bounds/volumes.
- Shell STEP reimport and measured blender cavity volume.
- Every listed arm target reachable with FK matching its TCP; leg link lengths
  and nonnegative foot clearance.
- Held-object transforms and scoop bowl centering over the cup.
- Cap rotation/axial pitch accounting and a pure torque feedback policy.
- Recipe headspace, supply, scoop count and open-vessel preconditions.
- B-rep intersections for arms versus shell/faceplate/worktop at key poses,
  and held scoop/carafe versus palm/wrist and stationary vessel walls.
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

Intermediate trajectory collision freedom and all-pairs interference are not
qualified. No balancing controller, drivetrain, fabricated gimbal, sensors,
gripper force control, vendor threads, measured cap damage/reopening torques,
calibrated powder dosing or fluid dynamics are implemented. The fixture rings
are packaging envelopes with clearance; actual clamps must be developed to
react cap torque. Printable studies require manufacturing development.

Run `.\run.ps1 test` or `./run.sh test`, followed by the demo, to reproduce the
digital evidence. Machine-specific artifacts and protocol logs remain in
ignored `builds/`. A passing build does not authorize physical operation.
