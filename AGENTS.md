# Machine CAD Agent

Personal hobby and learning project developed with AI assistance. Pocket Pal
is a digital robot concept. Distinguish agent-run checks from owner-reviewed
or physical work.

- Python under `src/machine_cad/` and `configs/pocket_pal.json` are authoritative.
- Execute builds and tests in the `dev` Docker Compose service.
- Dimensions use mm, recipe volumes mL, torque N m. Keep named components,
  held-object transforms, FK evidence and build provenance explicit.
- Rebuild after edits, read all failures, and inspect rendered PNGs. Do not
  claim an image was checked by a VLM unless that happened.
- Pass covers the exact scope in the report. Never turn nominal thread,
  torque, purchased-component or walking inputs into physical claims.
- Digital pose playback and browser speech/human actions control no hardware.
- Failed/stale builds must not expose fabrication exports through MCP/UI.
- Generated artifacts belong in ignored `builds/`. Keep credentials outside
  source, generated files, images and shared container mounts.
- Run meaningful geometry, STEP roundtrip and real MCP tests after changes.
- Only one coding agent edits this working tree at a time.
