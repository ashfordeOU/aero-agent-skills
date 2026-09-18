---
name: e2007-radiated-magnetic-susceptibility-procedure
description: "Audit one radiated magnetic susceptibility run under ECSS-E-ST-20-07C clause 5.4.10.4: confirm the mandatory steps were all carried out and in their proper order, compare the instrument soak against the required warm-up, judge the system verification read-back error against its decibel tolerance, size the tuned point count from the proportional frequency step, derive the dwell floor at the bottom of the band and the sweep time the run occupies, then take the threshold search down to the level the unit reacts at and report the margin it leaves. Use when running or reviewing a stepped magnetic exposure sweep on a built bench. Trigger: ecss, e-st-20-07c, radiated-magnetic-susceptibility-procedure, magnetic-exposure-instrument-warm-up, magnetic-field-system-verification-error, magnetic-exposure-frequency-stepping, magnetic-exposure-dwell-floor, magnetic-susceptibility-threshold-search."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-magnetic-susceptibility-procedure, radiated-magnetic-susceptibility-procedure, magnetic-exposure-instrument-warm-up, magnetic-field-system-verification-error, magnetic-exposure-frequency-stepping, magnetic-exposure-dwell-floor, magnetic-susceptibility-threshold-search]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Magnetic Susceptibility Procedure (space-systems/ecss/e2007-radiated-magnetic-susceptibility-procedure)

Use when the task is the run sequence of ECSS-E-ST-20-07C clause 5.4.10.4
-- the walk from switching the instruments on, through the check that
proves the loop is radiating what the drive claims, to the stepped
exposure sweep and the search for the level at which the unit reacts, and
the decision on whether the run as executed can be believed.

## Domain quick reference

- The clause is an ordered sequence, and the order carries meaning. A
  verification run after the sweep proves the chain was healthy at the
  end, not while the data was taken; a monitor baseline taken once the
  loop is already radiating proves nothing at all.
- Warm-up is a stability requirement on the source, the amplifier and the
  monitoring chain, not a courtesy. Amplifier gain and monitor thresholds
  drift for tens of minutes from cold, and a sweep started early carries
  that drift into every exposure as an unrecorded error.
- The verification is the only step that proves the field. A sense loop
  read back against a reference exercises the source, the amplifier, the
  cable and the loop together; every instrument can be in calibration
  while the chain still radiates the wrong level because a connector is
  loose or a winding is open.
- The read-back error is graded on its magnitude, so a chain radiating
  high fails on the same footing as one radiating low. A field above the
  intended level is a false pass waiting to be found in flight.
- Stepping is proportional, not linear. A fixed hertz step that is
  sensible at the top of the band walks over the whole bottom of it, so
  the step is a fraction of the tuned frequency and the point count comes
  from the ratio the band spans.
- Dwell per point is bounded below twice over: by the monitored
  function's own response time, and by a whole number of cycles at the
  tuned frequency. At the bottom of the band the cycle term governs, and
  a dwell chosen for the top of the band is far too short there.
- Sweep time is derived, not estimated. Points times dwell is the number
  that collides with the time the chamber is booked for, and deriving it
  before the run is what stops the step being coarsened halfway through.
- A reaction is not the end of the run. The level is stepped down until
  the indication ceases, and the threshold that falls out is compared
  with the required exposure level; the margin, signed, is the result the
  report carries.

## Workflow

1. Normalize the executed steps, reject a repeat, and reduce the list to
   the absent steps and the inversions in the executed order.
2. Compare the elapsed soak with the required warm-up and keep the
   headroom; a soak that only just reaches the requirement is a margin
   worth recording.
3. Compute the magnitude of the verification read-back error and compare
   it with the decibel tolerance, absorbing representation error only.
4. Derive the tuned point count from the band ratio and the proportional
   step fraction.
5. Derive the dwell floor at the bottom of the band from the monitor
   response and the required cycle count, and compare the planned dwell
   with it.
6. Multiply points by dwell for the sweep time and compare it with the
   time the run is allowed when one is stated.
7. When a reaction was seen, count the reduction steps down to the
   threshold and compute the margin it leaves over the required level.
8. Aggregate the findings and the limitations. The run stands only when
   no finding stands.

## Pitfalls

- Treating the step list as a checklist rather than a sequence, so every
  step is ticked and the verification happened after the sweep.
- Starting the sweep while the amplifier is still warming because the
  slot is tight, then attributing the drift to the unit.
- Skipping the verification on the grounds that every instrument is in
  calibration. Calibration is per instrument; the check is per chain.
- Grading the read-back error with a sign, so a loop radiating high is
  waved through while one radiating low is rejected.
- Stepping the sweep in fixed hertz, which is fine at the top of the band
  and walks straight over the bottom two decades of it.
- Choosing one dwell for the whole sweep from the top of the band, so
  every low-frequency point is read before a single cycle has completed.
- Stopping at the first reaction and reporting a susceptibility without
  taking the search down to the threshold, which leaves no margin figure
  at all.
- Discovering the sweep time only once the run is going, and coarsening
  the step mid-run so two halves of the record were taken under different
  settings.

## Behavior contract (gate 3)

The step sequencing and inversion detection, warm-up headroom,
verification-error grading, proportional step and point-count derivation,
dwell-floor and sweep-time arithmetic, threshold-search depth, margin
computation and run aggregation logic is exercised by the gate 3 contract
test:
scripts/test_e2007_radiated_magnetic_susceptibility_procedure.py against
scripts/e2007_radiated_magnetic_susceptibility_procedure_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_radiated_magnetic_susceptibility_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
