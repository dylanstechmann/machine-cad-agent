# Machine CAD Agent

This is a personal hobby and learning project developed with AI assistance. The
M01 pilot is a new gantry geometry study inspired by the layout in
https://github.com/dylanstechmann/diaper-changing-machines. It is not a converted
Blender model, built machine, or validated device.

- Python in `src/machine_cad/` and `configs/m01.json` are authoritative.
- Use `docker compose run --rm dev python -m machine_cad ...` for execution.
- Make dimensions explicit in millimeters, preserve named parts and provenance.
- Start by inspecting parameters and the current report. After a change, rebuild,
  read every failure, and inspect rendered PNGs. Numerical checks determine fit;
  images help inspect layout. Do not claim a VLM checked an image unless it did.
- A passing report covers solid validity and the stated sampled clearances only.
  It establishes no strength, wear, hygiene, control, or child-use safety claims.
- Stock profiles, rails and bushings are simplified nominal envelopes. Do not
  imply vendor compatibility without adding a sourced dimensional drawing.
- Failed builds must not produce fabrication exports. Generated files belong in
  `builds/`; change source or parameters to revise a design.
- Keep MCP stdout reserved for protocol traffic and tools confined to this project.
- Run the meaningful geometry, export roundtrip, and MCP tests after code changes.
- Only one coding agent may edit this working tree at a time.
