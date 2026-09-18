---
name: e2007-radiated-magnetic-susceptibility-setup
description: "Verify the bench arrangement a radiated magnetic susceptibility run is exposed on under ECSS-E-ST-20-07C clause 5.4.10.3: grade the loop standoff at every exposure surface against its window, cap the scan-grid spacing at the loop diameter so no lane of the surface goes unswept, confirm each position receives all three orthogonal loop presentations, derive the exposure count the arrangement implies, and prove the system verification sense loop reads back a voltage the monitor can resolve, separating outright deviations from dimensions merely sitting at a window edge. Use when building or auditing a magnetic exposure bench before the sweep starts. Trigger: ecss, e-st-20-07c, radiated-magnetic-susceptibility-setup, magnetic-loop-standoff-window, magnetic-exposure-scan-grid, orthogonal-loop-orientations, magnetic-field-sense-loop-verification, magnetic-exposure-surface-coverage."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-magnetic-susceptibility-setup, radiated-magnetic-susceptibility-setup, magnetic-loop-standoff-window, magnetic-exposure-scan-grid, orthogonal-loop-orientations, magnetic-field-sense-loop-verification, magnetic-exposure-surface-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Magnetic Susceptibility Setup (space-systems/ecss/e2007-radiated-magnetic-susceptibility-setup)

Use when the task is the exposure arrangement of ECSS-E-ST-20-07C clause
5.4.10.3 -- where the radiating loop is held relative to the unit and its
harness, how the loop is stepped and turned over each exposed surface,
and how the arrangement is proven to be producing the field before any
sweep is run.

## Domain quick reference

- Standoff is a dimension with a window, not a preference. The on-axis
  field falls off steeply with distance, so a loop held a couple of
  centimetres further back exposes the unit to a fraction of the level
  the record claims, and two runs at different standoffs are not
  comparable.
- Spacing between loop positions is bounded by the loop itself.
  Successive positions have to overlap, so the step cannot exceed the
  loop diameter; stepping wider leaves a lane of the surface that was
  never inside the field at all.
- One orientation is not an exposure. A loop presented in a single plane
  drives flux through one axis of the unit, and a victim loop lying in
  that plane sees almost nothing; each position therefore receives all
  three orthogonal presentations.
- The harness is an exposure position in its own right. Long runs close
  the largest loops on the bench and are frequently more susceptible than
  any face of the unit, so the loop is walked along them as it is over
  the structure.
- The verification arrangement proves the field, not the setting. A sense
  loop of known turns and area held in the field reads back a voltage
  that scales with frequency as well as with flux density, and that
  read-back is the only evidence the loop is radiating what the drive
  says it is.
- That read-back has to sit above the monitor floor. At the bottom of the
  band the induced voltage is small, and a verification that cannot be
  resolved there proves the arrangement only where it was never in doubt.
- Exposure count is derived, not estimated. Grid positions times
  orientations times surfaces is the number that collides with the time
  the chamber is booked for, and deriving it before the run is what stops
  the grid being coarsened halfway through.
- A dimension inside its window but close to the edge is a limitation to
  carry, not a deviation to raise. Keeping the two apart stops a bench
  being rebuilt over a millimetre and stops a real deviation being filed
  as a rounding matter.

## Workflow

1. Normalize each exposure position to a recognized surface or harness
   run and reject a surface appearing twice; a duplicate means two runs
   were merged.
2. Validate each position: positive extents, a non-negative standoff, a
   positive grid spacing and a non-empty orientation list with no
   presentation repeated.
3. Grade the standoff against its window, splitting the result into
   conforming, marginal or deviation.
4. Derive the spacing ceiling from the loop diameter and compare the
   planned grid spacing with it.
5. List the orthogonal presentations a position never received.
6. Compute the grid over each surface and multiply by the orientations
   for the exposure count the arrangement implies.
7. Derive the sense-loop read-back from the turns-area product, the
   wanted flux density and the frequency, and compare it with the monitor
   floor.
8. Aggregate: per-position deviations first, with the marginal dimensions
   carried separately as limitations. The bench conforms only when no
   finding stands.

## Pitfalls

- Holding the loop wherever the structure allows and treating standoff as
  a nominal figure, then comparing the run against one taken at the
  window centre.
- Stepping the loop by its own radius in one axis and by a hand's width
  in the other, so one direction is swept twice over and the other has
  gaps.
- Presenting the loop in one plane per face because three passes will not
  fit the booking, and missing the axis the victim loop actually lies in.
- Sweeping the structure and skipping the harness runs, which close the
  largest loops on the bench.
- Treating the amplifier setting as proof of the field. The sense loop is
  the only thing that shows what was radiated.
- Choosing a sense loop with a small turns-area product and discovering
  at the bottom of the band that its read-back is under the monitor
  floor.
- Discovering the exposure count only once the sweep is running, then
  coarsening the grid so two halves of the record were taken on different
  arrangements.
- Filing every millimetre at the window edge as a deviation, so the real
  deviations stop being read.

## Behavior contract (gate 3)

The surface and orientation normalization, position validation, windowed
standoff grading, spacing-ceiling and scan-grid derivation, sense-loop
read-back arithmetic and conformance aggregation logic is exercised by
the gate 3 contract test:
scripts/test_e2007_radiated_magnetic_susceptibility_setup.py against
scripts/e2007_radiated_magnetic_susceptibility_setup_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_radiated_magnetic_susceptibility_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
