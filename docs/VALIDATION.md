# Validation record

These checks are executed by an AI coding agent in the pinned Docker runtime.
They are digital analyses, not tests personally performed or reviewed by the
owner. No physical fabrication or machine operation has been performed.

## Automated checks

The test suite covers:

- 21 valid, closed, single-solid baseline components.
- Actual plate bounds and solid volume after eight 4.5 mm through holes.
- Measured 0.25 mm block-to-rail radial gap at all default sample positions.
- Excess travel producing real positive-volume intersection with supports.
- An independent travel gate rejecting a 2,000 mm span even with only three
  samples, when sampled positions otherwise miss the end-support collision.
- Invalid/unknown/non-finite parameter rejection.
- Plate STEP export and reimport preserving bounds and volume.
- Failed builds keeping PNG previews while withholding STEP/STL.
- Rejection of build path traversal.
- A real stdio MCP client discovering tools, building, measuring, receiving
  six native PNG images, listing passing exports, and receiving explicit
  errors for failed exports and invalid inputs.

Run `./run.sh test` or `.\run.ps1 test` to reproduce. GitHub CI performs the
same checks, followed by the deterministic pass/fail/pass demo.

## Geometric interpretation

The baseline has 360 mm total carriage travel. A conservative X envelope
limits the default layout to 448 mm, retaining the generic 2 mm end-support
gap. The deliberately broken demo uses 500 mm travel; endpoint checks report
plate/support overlaps in addition to the travel-envelope failure. The
repaired revision restores 360 mm travel.

The checker measures moving components against stationary obstacles and
rails. Intentional static mating contacts and plate-to-block contacts are
excluded. Motion positions are sampled; the analytic travel gate addresses
the known end-support / rail-engagement envelope, not arbitrary continuous
collision certification.

There is no load analysis, tolerance-stack study, purchased-component fit
verification, print process qualification, electrical/control validation,
or physical safety testing in this project.
