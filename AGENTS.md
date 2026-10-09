# Machine CAD Agent

Personal hobby and learning project developed with AI assistance. Pocket Pal
is a digital robot concept. Distinguish agent-run checks from owner-reviewed
or physical work.

- Python under `src/machine_cad/` and `configs/pocket_pal.json` are authoritative.
- Execute builds and tests in the `dev` Docker Compose service.
- Dimensions use mm, recipe volumes mL, torque N m. Keep named components,
  held-object transforms, FK evidence and build provenance explicit.
- Inspect paged motion evidence and failing-sample images. Intermediate
  samples must retain cap winding, scoop bowl centering and discrete events.
  Incomplete sampling or unexplained ownership transitions withhold exports.
- Rebuild after edits, read all failures, and inspect rendered PNGs. Do not
  claim an image was checked by a VLM unless that happened.
- Pass covers the exact scope in the report. Never turn nominal thread,
  torque, purchased-component or walking inputs into physical claims.
- Digital pose playback and browser speech/human actions control no hardware.
- Keep product evidence, nominal CAD inputs and simulation assumptions distinct.
  Null measurements are unknown. Owned-product fit and manufacturing release
  remain pending even when generic design-study exports pass.
- Simulation episodes must advance through motor commands and physics steps.
  Preserve fixed input snapshots and compare learned policies on held-out seeds.
  Inspect effort/contact/termination evidence and rendered simulation views.
- Failed/stale builds must not expose fabrication exports through MCP/UI.
- Generated artifacts belong in ignored `builds/`. Keep credentials outside
  source, generated files, images and shared container mounts.
- Run meaningful geometry, STEP roundtrip and real MCP tests after changes.
- Only one coding agent edits this working tree at a time.
